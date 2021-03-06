#!/usr/bin/env python2.7
import os, sys, pty

def run(cmd):
    retval = os.system(cmd)

    if retval != 0:
        print "Failure running", cmd
        sys.exit(retval)

def gpg(*args):
    argv = ['gpg'] + list(args)
    for n in xrange(3):
        pty.spawn(argv)
        pid, status = os.wait()
        status = os.WEXITSTATUS(status)
        if status == 0:
            break
    else:
        print 'Failure running', ' '.join(argv)
        sys.exit(status)

def expand_path(path):
    sudo_user = os.environ.get('SUDO_USER', '')
    if path[0] == '~':
        path = os.path.expanduser("~%s%s" % (sudo_user, path[1:]))
    return path

def shred(*fs):
    for f in fs:
        if os.path.exists(f):
            run('shred -uf %s' % f)

def exist(*fs):
    for f in fs:
        if not os.path.exists(f):
            print >>sys.stderr, 'Missing: %s' % f
            sys.exit(1)

def decrypt():
    exist('secret.tar.gpg')
    shred('secret.tar')
    print 'Decrypting: secret.tar <- secret.tar.gpg'
    gpg('--yes', 'secret.tar.gpg')

def encrypt():
    exist('secret.tar')
    shred('secret.tar.gpg')
    print 'Encrypting: secret.tar -> secret.tar.gpg'
    gpg('-c', 'secret.tar')
    shred('secret.tar')

def maybe_extract_list():
    if not os.path.exists('secret.lst'):
        print 'Extracting: secret.lst'
        decrypt()
        run('tar f secret.tar -xpP "%s"' % expand_path('~/.secret/secret.lst'))
        run('chown %s: secret.tar.gpg' % os.environ.get('SUDO_USER'))

def save():
    maybe_extract_list()
    shred('secret.tar')
    # run('touch secret.tar')
    def add(path):
        path = expand_path(path)
        print 'Saving: %s' % path
        run('tar f secret.tar -upP -- "%s"' % path)
    for line in open('secret.lst'):
        line = line.strip()
        if not line or line[0] == '#':
            continue
        add(line)
    add('~/.secret/secret.lst')
    encrypt()
    user = os.environ.get('SUDO_USER')
    run('su %s -c "vcsh secret add secret.tar.gpg"' % user)
    run('su %s -c "vcsh secret commit -m secret"' % user)
    run('su %s -c "vcsh secret push"' % user)

def restore():
    user = os.environ.get('SUDO_USER')
    run('su %s -c "vcsh secret pull"' % user)
    decrypt()
    run('tar f secret.tar -xpPv --overwrite')
    shred('secret.tar')

if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('save', 'restore'):
        print >>sys.stderr, 'usage: %s save|restore' % sys.argv[0]
        sys.exit(0)
    if os.getuid() != 0:
        os.execlp('sudo', 'sudo',
                  'SSH_AUTH_SOCK=%s' % os.getenv('SSH_AUTH_SOCK', ''),
                  sys.executable,
                  *sys.argv)
    os.chdir(os.path.dirname(__file__))
    if sys.argv[1] == 'save':
        save()
    else:
        restore()
