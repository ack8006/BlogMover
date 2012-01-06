#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       untitled.py
#
#       Copyright 2011 andy <andy@math-is-fun>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.
#
#



def main():
    f = open('htaccess_example.txt', 'a')
    print >> f,'# Helicon ISAPI_Rewrite configuration file\n# Version 3.1.0.57\n\n\nRewriteEngine On\nRewriteCompatibility2 On\nRepeatLimit 200\n\n'
    g = open('example_map.log')
    h = g.readlines()
    g.close()
    for line in h:
        if len(line) and 'http' in line:
            startexp = '^' + line.split(',')[0]
            endexp = line.split(',')[1].split('\n')[0]
            rule = ' '.join(['RewriteRule', startexp, endexp, '[R,L,NC]'])
            if 'examples' in line:
                print >> f, rule
    f.write('''\n\n# Firefox rewrite\nRewriteRule ^([a-zA-Z%0-9\-_/\s\+]*)/{0,1}$ $1/Default.aspx?RewriteStatus=1 [NC,L]\n#  Handle query string\nRewriteRule ^([a-zA-Z%0-9\-_/\s\+]*)\?(.*)$ $1/Default.aspx?RewriteStatus=3&$2 [NC,L]\n#  Internet Explorer\nRewriteRule ^http://([a-zA-Z0-9\-\.]+)/{0,1}([a-z%A-Z0-9\-_/\s\+]*)/{0,1}$ /$2/Default.aspx?RewriteStatus=2 [NC,L]\n\n# Handle query string\nRewriteRule ^http://([a-zA-Z0-9\-\.]+)/([a-zA-Z0-9\-_/\s\+]*)\?(.*)$ /$2/Default.aspx?RewriteStatus=3&$3 [NC,L]\n\n    ''')
    f.close()
    return 0

if __name__ == '__main__':
    main()

