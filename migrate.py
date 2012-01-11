#!/usr/bin/env python

import urllib2
import httplib
import simplejson as json
import sys
import datetime
import socket
import time


class Args:
    
    accepted_args = ['--source_portal', '-sp', '--source_key', '-sk', '--target_portal', '-tp', '--target_key', 
                    '-tk', '--source_blog_guid', '-sb', '--target_blog_guid', '-tb', '--include_comments', '-ic', 
                    '--target_author_email', '-te']
    required_args = ['--source_portal', '--source_key', '--target_portal', '--target_key', '--target_author_email']


class BlogMigration(Args):

    def __init__(self, options):
        # set source params
        self.source = dict()
        
        results = self.validate_API_Key(options['--source_key'])
        self.source['key'] = options['--source_key']
        self.validate_portal(results, options['--source_portal'])
        self.source['portal'] = options['--source_portal']
        
        self.source['guid'] = options.get('--source_blog_guid') or self.get_blog_guid('source')
        
        # set target params
        self.target = dict()
        results = self.validate_API_Key(options['--target_key'])
        self.target['key'] = options['--target_key']
        self.validate_portal(results, options['--target_portal'])
        self.target['portal'] = options['--target_portal']
        self.target['author_email'] = options['--target_author_email']
        self.target['guid'] = options.get('--target_blog_guid') or self.get_blog_guid('target')

        # include comments in the blog migration?
        self.include_comments = True
        if options.get('--include_comments') and options['--include_comments'].lower() != 'true':
            self.include_comments = False
            
        self.retries = [1,10,30]
    
        self.file ='/Users/atakata/Desktop/%s.csv'

    def get_posts_decorator(targetFunction):
        def _inner(a,b,c,d):
            length = len(targetFunction(a,b,c,d))
            postsString = ' '.join(['Posts to Copy:', str(length)])
            print "Got %s blog posts" % length
            curDate = str(datetime.datetime.now())
            with open(a.file % 'log', 'a') as f:
                print >> f, curDate
                print >> f, 'SourcePortal: ', a.source['portal']
                print >> f, 'BlogGUID: ', a.source['guid']
                print >> f, postsString
                print >> f, 'PostGuid, JSONURL, PostURL, JSONGuid'
            with open(a.file %'errorLog', 'a') as f:
                print >> f, curDate
                print >> f, 'SourcePortal: ', a.source['portal']
                print >> f, 'BlogGUID: ', a.source['guid']
                print >> f, postsString
                print >> f, 'URLPath, BlogGuid, ResponseCode'
            return targetFunction(a,b,c,d)
        return _inner
    
    def error_observer_decorator(targetFunction):
        def _inner(a,b,c,d,e):
            with open(a.file %'errorLog', 'a') as f:
                s = [str(c),str(d),str(e)]
                d = ', '.join(s)
                print >> f, d
            return targetFunction(a,b,c,d,e)
        return _inner
    
    def observer_decorator(targetFunction):
        def _inner(a,b,c):
            with open(a.file %'log', 'a') as f:
                t = targetFunction(a,b,c)
                s = [t['PostGuid'], t['JSONURL'], t['PostURL'], t['JSONGuid']]
                print >> f, ', '.join(s)
            return targetFunction(a,b,c)
        return _inner
    
    def validate_API_Key(self, key):
        if key == 'quit':
            sys.exit(-1)
        url = 'http://hubapi.com/settings/v1/settings?hapikey=%s' % key
        e = 'Migrate4EELZZZZZ'
        while e:
            try:
                url = 'http://hubapi.com/settings/v1/settings?hapikey=%s' % key
                result = json.load(urllib2.urlopen(url))
                e = None
            except Exception as e:
                key = raw_input("API Source Key invalid, please reenter key or enter quit to exit \n")
                continue
        print('key validated')
        return result

    def validate_portal(self, results, portal):
        while not str(results[0]['portalId']) == str(portal):
            if portal == 'quit':
                sys.exit(-1)
            portal = raw_input("Source Portal invalid, please reenter portal or enter quit to exit \n")
        print('portal validated')
    
    def get_blog_guid(self, option):
        portal, key = (self.source['portal'], self.source['key']) if option == 'source' \
            else (self.target['portal'], self.target['key'])
        blogs_dict = self.get_blog_titles(key, portal)
        sorted_keys = sorted(blogs_dict.keys())
        print 'available %s blogs:' % option
        for index, key in enumerate(sorted_keys):
            print "%s: %s" % (index, key)
        blog_selection = raw_input("Please choose a blog:\n>")
        return blogs_dict[sorted_keys[int(blog_selection)]]
 
    def get_blogs(self, api_key, portal_id):
        url = 'https://hubapi.com/blog/v1/list.json?hapikey=%s&portalId=%s'
        blogs = json.load(urllib2.urlopen(url % (api_key, portal_id)))
        return blogs

    def get_blog_titles(self, api_key, portal_id):
        blogs = self.get_blogs(api_key, portal_id)
        blog_title_dict = dict((blog['blogTitle'], blog['guid']) for blog in blogs)
        return blog_title_dict
    
    @get_posts_decorator
    def get_posts(self, blog_guid, api_key, portal_id):
        posts = []
        offset = 0
        url = "https://hubapi.com/blog/v1/%s/posts.json?hapikey=%s&portalId=%s&max=100&offset=%s"
        running = True
        while running:
            data = json.load(urllib2.urlopen(url % (blog_guid, api_key, portal_id, offset)))
            posts += data
            if not data:
                running = False
            offset += 100
        return posts

    def sleep_check(self, stat, path, body, headers):  
        conn = httplib.HTTPSConnection('hubapi.com')  
        for sleep_time in self.retries:
            conn.request(stat, path, body, headers)
            try:
                response = conn.getresponse()
                return response
            except socket.error:
                print('Socket Timeout, Will Retry Soon')
                time.sleep(sleep_time)
                continue
            except socket.gaierror:
                print('GAIError')
                time.sleep(sleep_time)
                continue
            except urllib2.URLError as e:
                print e
                time.sleep(sleep_time)
                continue
            except Exception as e:
                break
        return None

    def get_comments_for_blog(self, blog_guid, api_key, portal_id):
        comments = []
        offset = 0
        url = "https://hubapi.com/blog/v1/%s/comments.json?hapikey=%s&portalId=%s&offset=%s&max=100"
        running = True
        while running:
            data = json.load(urllib2.urlopen(url % (blog_guid, api_key, portal_id, offset)))
            comments += data
            if not data:
                running = False
            offset += 100
        return comments

    def make_post_comment(self, post_guid, api_key, portal_id, anonyName, anonyEmail, comment, anonyUrl):
        headers = {"Content-type": "application/json"}
        retries = [1,10,100]
        body = json.dumps(
            dict(
                anonyName = anonyName,
                anonyEmail = anonyEmail,
                comment = comment,
                anonyUrl = anonyUrl,
                ))
        path = '/blog/v1/posts/%s/comments.json?hapikey=%s&portalId=%s' % (post_guid, api_key, portal_id)
    
        response = self.sleep_check("POST", path, body, headers)
        
        if response:
            print response.status
            if response.status < 400:
                response_body = response.read()
                print response_body
                return response_body
            else:
                self.error_comment_observer(response, path, blogGuid, response.status)
                raise Exception(str(response.status))
                #return None
        else:
            self.error_comment_observer(response, path, blogGuid, response.status)
            return None
        
    @error_observer_decorator
    def error_comment_observer(self, response, path, blogGuid, status):
        print response.read()
        errorDict = {'URLPath':path, 'BlogGuid':blogGuid, 'ResponseCode':status}
        return errorDict
    
    @error_observer_decorator    
    def error_observer(self, response, path, blogGuid, status):
        print('Error Observer =',response.read())
        errorDict = {'URLPath':path, 'BlogGuid':blogGuid, 'ResponseCode':status}
        return errorDict 
        
    def make_blog_post(self, blogGuid, api_key, portal_id, authorEmail, body, summary, title, tags, metaDesc, metaKeys):
        headers = {"Content-type": "application/json"}
        retries = [1,10,100]
        body = json.dumps(
            dict(
                authorEmail = authorEmail,
                body = body,
                summary = summary,
                title = title,
                tags = tags,
                metaDesc = metaDesc,
                metaKeys = metaKeys,
                ))
        path = '/blog/v1/%s/posts.json?hapikey=%s&portalId=%s' % (blogGuid, api_key, portal_id)
        
        response = self.sleep_check("POST", path, body, headers)
        
        print('responseresponse')
        print response
        
        if response:
            print('RESPONSESTATUS:', response.status)
            if response.status < 400:
                response_body = response.read()
                print response_body
                return response_body
            else:
                print('ERRORFOUNDHERE')
                self.error_observer(response, path, blogGuid, response.status)
                raise Exception(str(response.status))
                #return None
        else:
            self.error_observer(path, response, blogGuid, response.status)
            return None
    
    @observer_decorator
    def post_observer(self, post, json):
        return {'PostGuid' : post['guid'], 'PostURL':post['url'], 'JSONGuid':json['guid'], 'JSONURL':json['url']}
    
    def make_posts(self, posts, email, blog_guid, portal_id, api_key):
        guid_map = []
        url_map = []
        for post in posts:
            print('New Post')
            try:
                response = self.make_blog_post(blog_guid, api_key, portal_id, email, post['body'], post['summary'], 
                    post['title'], post['tags'], post['metaDescription'], post['metaKeywords'])
            except Exception as e:
                print('error =', e)
                continue
            if response:
                json_resp = json.loads(response)
                self.post_observer(post, json_resp)
                guid_map.append((post['guid'], json_resp['guid']))
                url_map.append((post['url'], json_resp['url']))
                
        
        return {'guids': guid_map, 'urls': url_map}

    def update_comments(self, comments, guid_map):
        for comment in comments:
            for pair in guid_map:
                if str(comment['postGuid']) == pair[0]:
                    comment['postGuid'] = pair[1]
        return comments

    def create_comments(self, comments, portal_id, api_key):
        for comment in comments:
            try:
                response = self.make_post_comment(comment['postGuid'], api_key, portal_id, comment['anonyName'], 
                    comment['anonyEmail'], comment['comment'], comment['anonyUrl'])
                print response
            except Exception as e:
                print >> sys.stderr, e

    def do_migration(self):
        posts_to_move = self.get_posts(self.source['guid'], self.source['key'], self.source['portal'])
        maps_dict = self.make_posts(posts_to_move, self.target['author_email'], self.target['guid'], 
            self.target['portal'], self.target['key'])
        
        print maps_dict['urls']
        if self.include_comments:
            comments_to_move = self.get_comments_for_blog(self.source['guid'], self.source['key'], self.source['portal'])
            updated_comments = self.update_comments(comments_to_move, maps_dict['guids'])
            self.create_comments(updated_comments, self.target['portal'], self.target['key'])
            
    
class Parser(Args):

    def clean_up_dict(self, options_dict):
        mappings = {'-sp' : '--source_portal', '-sk' : '--source_key', '-tp' : '--target_portal', 
                    '-tk' : '--target_key', '-sb' : '--source_blog_guid', '-tb' : '--target_blog_guid', 
                    '-ic' : '--include_comments', '-te' : '--target_author_email'} 
        for key in mappings.keys():
            if key in options_dict.keys():
                options_dict[mappings[key]] = options_dict[key]
                del options_dict[key]
        return options_dict

    def parse_options(self, option_list):
        used_args = [arg for arg in Parser.accepted_args for option in option_list if arg in option]
        opt_dict = dict()
        for used_arg in used_args:
            a = [option.split('=') for option in option_list if used_arg in option][0]
            opt_dict[a[0]] = a[1]
        clean_dict = self.clean_up_dict(opt_dict)
        if all(req_arg in clean_dict.keys() for req_arg in Parser.required_args):
            return opt_dict
        return None

def main():
    parser = Parser()
    args = parser.parse_options(sys.argv[1:])
    if not args:
        print 'usage: migrate.py <--source_portal> <--source_key> <--target_portal> <--target_key> <--target_author_email> [--source_blog_guid] [--target_blog_guid] [--include_comments]'
        sys.exit(-1)
    migration = BlogMigration(args)
    migration.do_migration()
    migration.print_migration()

if __name__ == '__main__':
    main()
