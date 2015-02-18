#!/usr/bin/env python2.7
import os, sys

def run(cmd):
    retval = os.system(cmd)

    if retval != 0:
        print "Failure running", cmd
        sys.exit(retval)

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
    run('gpg --yes secret.tar.gpg')

def encrypt():
    exist('secret.tar')
    shred('secret.tar.gpg')
    print 'Encrypting: secret.tar -> secret.tar.gpg'
    run('gpg -c secret.tar')
    shred('secret.tar')

def maybe_extract_list():
    if not os.path.exists('secret.lst'):
        print 'Extracting: secret.lst'
        decrypt()
        run('tar f secret.tar -xpP "%s"' % expand_path('~/.secret/secret.lst'))

def save():
    maybe_extract_list()
    shred('secret.tar')
    # run('touch secret.tar')
    for line in open('secret.lst'):
        line = line.strip()
        if not line or line[0] == '#':
            continue
        path = expand_path(line)
        run('tar f secret.tar -upP --add-file="%s"' % path)
    encrypt()
    run('vcsh secret add secret.tar.gpg')
    run('vcsh secret commit -m "secret"')
    run('vcsh secret push')

def restore():
    run('vcsh secret pull')
    decrypt()
    run('tar f secret.tar -xpP --overwrite')
    shred('secret.tar')

if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('save', 'restore'):
        print >>sys.stderr, 'usage: %s save|restore' % sys.argv[0]
        sys.exit(0)
    if os.getuid() != 0:
        os.execlp("sudo", "sudo", "python", *sys.argv)
    os.chdir(os.path.dirname(__file__))
    if sys.argv[1] == 'save':
        save()
    else:
        restore()
