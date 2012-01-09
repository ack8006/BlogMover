#!/usr/bin/env python

def main():
    with open('htaccess_example.txt', 'a') as f:
        with open('example_map.log') as g:
            h = g.readlines()
        print >> f,'# Helicon ISAPI_Rewrite configuration file\n# Version 3.1.0.57\n\n\nRewriteEngine On\nRewriteCompatibility2 On\nRepeatLimit 200\n\n'
        for line in h:
            if len(line) and 'http' in line:
                startexp = '^' + line.split(',')[0]
                endexp = line.split(',')[1].split('\n')[0]
                rule = ' '.join(['RewriteRule', startexp, endexp, '[R,L,NC]'])
                if 'examples' in line:
                    print >> f, rule
        print >> f, '\n\n# Firefox rewrite\nRewriteRule ^([a-zA-Z%0-9\-_/\s\+]*)/{0,1}$ $1/Default.aspx?RewriteStatus=1 [NC,L]'
        print >> f, '#  Handle query string\nRewriteRule ^([a-zA-Z%0-9\-_/\s\+]*)\?(.*)$ $1/Default.aspx?RewriteStatus=3&$2 [NC,L]'
        print >> f, '#  Internet Explorer\nRewriteRule ^http://([a-zA-Z0-9\-\.]+)/{0,1}([a-z%A-Z0-9\-_/\s\+]*)/{0,1}$ /$2/Default.aspx?RewriteStatus=2 [NC,L]\n'
        print >> f, '# Handle query string\nRewriteRule ^http://([a-zA-Z0-9\-\.]+)/([a-zA-Z0-9\-_/\s\+]*)\?(.*)$ /$2/Default.aspx?RewriteStatus=3&$3 [NC,L]\n'
    return 0

if __name__ == '__main__':
    main()

