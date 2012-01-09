#!/usr/bin/env python

import urllib2
import httplib
import simplejson as json
import sys

class Args:
    
    accepted_args = ['--source_portal', '-sp', '--source_key', '-sk', '--target_portal', '-tp', '--target_key', 
                    '-tk', '--source_blog_guid', '-sb', '--target_blog_guid', '-tb', '--include_comments', '-ic', 
                    '--target_author_email', '-te']
    required_args = ['--source_portal', '--source_key', '--target_portal', '--target_key', '--target_author_email']

class BlogMigration(Args):

    def __init__(self, options):
        #set source params
        self.source = dict()
        self.source['portal'] = options['--source_portal']
        self.source['key'] = options['--source_key'] 
        self.source['guid'] = options.get('--source_blog_guid') or self.get_blog_guid('source')
        
        self.target = dict()
        self.target['portal'] = options['--target_portal']
        self.target['key'] = options['--target_key']
        self.target['author_email'] = options['--target_author_email']
        self.target['guid'] = options.get('--target_blog_guid') or self.get_blog_guid('target')

        # include comments in the blog migration?
        self.include_comments = True
        if options.get('--include_comments') and options['--include_comments'].lower() != 'true':
            self.include_comments = False

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
        print "Got %s blog posts" % len(posts)
        return posts

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

    def make_blog_post(self, blogGuid, api_key, portal_id, authorEmail, body, summary, title, tags, metaDesc, metaKeys):
        headers = {"Content-type": "application/json"}
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
        conn = httplib.HTTPSConnection('hubapi.com')
        path = '/blog/v1/%s/posts.json?hapikey=%s&portalId=%s' % (blogGuid, api_key, portal_id)
        conn.request("POST", path, body, headers)
        response = conn.getresponse()
        print response.status
        if response.status < 400:
            response_body = response.read()
            print response_body
            return response_body
        print response.read()
        return response.status

    def make_post_comment(self, post_guid, api_key, portal_id, anonyName, anonyEmail, comment, anonyUrl):
        headers = {"Content-type": "application/json"}
        body = json.dumps(
            dict(
                anonyName = anonyName,
                anonyEmail = anonyEmail,
                comment = comment,
                anonyUrl = anonyUrl,
                ))
        conn = httplib.HTTPSConnection('hubapi.com')
        path = '/blog/v1/posts/%s/comments.json?hapikey=%s&portalId=%s' % (post_guid, api_key, portal_id)
        conn.request("POST", path, body, headers)
        response = conn.getresponse()
        print response.status
        if response.status < 400:
            response_body = response.read()
            print response_body
            return response_body
        print response.read()
        raise Exception("An error ocurred creating a comment on post with ID: %s" % post_guid)

    def make_posts(self, posts, email, blog_guid, portal_id, api_key):
        guid_map = []
        url_map = []
        for post in posts:
            try:
                response = self.make_blog_post(blog_guid, api_key, portal_id, email, post['body'], post['summary'], 
                    post['title'], post['tags'], post['metaDescription'], post['metaKeywords'])
            except Exception as e:
                print e
                continue
            json_resp = json.loads(response)
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
                continue
        return 0

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

if __name__ == '__main__':
    main()
