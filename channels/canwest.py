from theplatform import *
from BeautifulSoup import BeautifulStoneSoup
try:
    from pyamf import remoting
    has_pyamf = True
except ImportError:
    has_pyamf = False

class CanwestBaseChannel(ThePlatformBaseChannel):
    is_abstract = True
    base_url = 'http://feeds.theplatform.com/ps/JSON/PortalService/2.2/'
    PID = None
    root_depth = 1

    def get_categories_json(self,arg=None):
        return ThePlatformBaseChannel.get_categories_json(self) # + '&query=ParentIDs|%s'%arg

    def get_releases_json(self,arg='0'):
        return ThePlatformBaseChannel.get_releases_json(self) + '&query=CategoryIDs|%s'% (self.args['entry_id'],)

    def children_with_releases(self, categorylist, cat):

        if cat['fullTitle'] == '':
            prefix = ''
        else:
            prefix = cat['fullTitle'] + "/"

        children = [c for c in categorylist \
                    if c['depth'] == cat['depth'] + 1 \
                    and c['fullTitle'].startswith(prefix) \
                    and (c['hasReleases'] or self.children_with_releases(categorylist, c))]
        return children


    def get_child_categories(self, categorylist, parent_id):

        show_empty = self.plugin.get_setting('show_empty_cat') == 'true'
        if parent_id is None:
            if self.root_depth > 0:
                cat = [c for c in categorylist if c['depth'] == self.root_depth - 1][0]
            else:
                cat = {'depth': -1, 'fullTitle': ''}
        else:
            logging.debug("ParentID: %s [%s]" % (parent_id, type(parent_id)))
            cat = [c for c in categorylist if c['ID'] == int(parent_id)][0]

        if cat['fullTitle'] == '':
            prefix = ''
        else:
            prefix = cat['fullTitle'] + "/"

        if show_empty:
            categories = [c for c in categorylist if c['depth'] == cat['depth'] + 1 \
                          and c['fullTitle'].startswith(prefix)]

        else:
            categories = self.children_with_releases(categorylist, cat)

        return categories


    #override ThePlatFormbase so ?querystring isn't included in playpath
    #this could be temp-only, actually. paypath doesn't seem to care about extra parameters
    def action_play(self):
        parse = URLParser(swf_url=self.swf_url, playpath_qs=False)
        self.plugin.set_stream_url(parse(self.args['clip_url']))



class GlobalTV(CanwestBaseChannel):
    short_name = 'global'
    long_name = 'Global TV'
    PID = 'W_qa_mi18Zxv8T8yFwmc8FIOolo_tp_g'
    swf_url = 'http://www.globaltv.com/widgets/ThePlatformContentBrowser/swf/flvPlayer.swf swfvfy=true'
    #swf_url = 'http://www.globaltv.com/video/swf/flvPlayer.swf'

    def get_categories_json(self,arg=None):
        url = CanwestBaseChannel.get_categories_json(self,arg) + '&query=CustomText|PlayerTag|z/Global%20Video%20Centre' #urlencode
        logging.debug('get_categories_json: %s'%url)
        return url

    def get_releases_json(self,arg='0'):
        url = '%s' % CanwestBaseChannel.get_releases_json(self,arg)
        logging.debug('get_releases_json: %s'%url)
        return url

class GlobalNewsTest(CanwestBaseChannel):
    base_url = 'http://globalnews.ca/national/videos'
    short_name = 'globalnewstest'
    long_name = 'Global News TEST'
    local_channels = [
        ('National','http://globalnews.ca/national/videos'),
        ('BC', 'http://globalnews.ca/national/videos'),
        ('Calgary', 'http://globalnews.ca/national/videos'),
        ('Halifax', 'http://globalnews.ca/national/videos'),
        ('Edmonton', 'http://globalnews.ca/national/videos'),
        ('Lethbridge', 'http://globalnews.ca/national/videos'),
        ('Montreal', 'http://globalnews.ca/national/videos'),
        ('New Brunswick', 'http://globalnews.ca/national/videos'),
        ('Regina', 'http://globalnews.ca/national/videos'),
        ('Saskatoon', 'http://globalnews.ca/national/videos'),
        ('Toronto', 'http://globalnews.ca/national/videos'),
        ('Winnipeg', 'http://globalnews.ca/national/videos'),
    ]

    def get_cache_key(self):
        return "%s-%s" % (self.short_name, self.args.get('local_channel',''))

    def action_root(self):
        for channel, ptag in self.local_channels:
            self.plugin.add_list_item({
                'Title': channel,
                'action': 'browse',
                'channel': self.short_name,
                'entry_id': None,
                'local_channel': channel
            })
        self.plugin.end_list()

    def action_browse(self):

        caturl = dict(self.local_channels)[self.args['local_channel']]

        #logging.debug('______________________________')
        #logging.debug('caturl: %s' % caturl)
        #logging.debug(self.args)
        #logging.debug('______________________________')

        soup = BeautifulSoup(self.plugin.fetch(caturl, max_age=self.cache_timeout))
        navlist = soup.findAll('div', 'video-navigation-column')

        for ltag in navlist:
            catlinks = ltag.findAll('a')

            for category in catlinks:
                data = {}
                data.update(self.args)

                tagline = category.string
                url = category['href']

                # TODO: replace first one with local channel link
                # because it comes in as /default/

                data.update({
                    'action': 'browse_category',
                    'Title': tagline,
                    'entry_id': None,
                    'remote_url': url
                })
                self.plugin.add_list_item(data)
        self.plugin.end_list()


    def action_browse_category(self):
        #logging.debug('______________________________')
        #logging.debug(self.args)
        logging.debug('______________________________')

        # using RSS cuz json was not working
        # json.loads was complaining
        platform_url = 'http://feed.theplatform.com/f/dtjsEC/FCT_FJTDVpVT?form=rss&byId=%s'

        soup = BeautifulSoup(self.plugin.fetch(self.args['remote_url'], max_age=self.cache_timeout))
        eplist = soup.find('ul', 'video-browse-container').findAll('li')

        #logging.debug(eplist)

        for ep in eplist:
            # TODO: need to parse this into minutes
            spans = ep.findAll('span')
            duration = spans[len(spans)-1].string

            tagline = ep.a['title']

            # TODO: not sure why this is not loading...
            thumb = ep.img['src']

            data = {}
            data.update(self.args)

            data.update ({
                'action': 'play_episode',
                'entry_id': None,
            	'Title': tagline,
            	#'Duration' : duration,
            	'Thumb' : thumb,
            	'tagline': tagline,
            	'remote_url': platform_url % ep.findAll('span')[1]['data-v_count_id']
            })
            self.plugin.add_list_item(data)
        self.plugin.end_list()

    def action_play_episode(self):
        #logging.debug('______________________________')
        #logging.debug(self.args)
        logging.debug('______________________________')

        data = self.plugin.fetch(self.args['remote_url'], self.cache_timeout).read()
        soup = BeautifulStoneSoup(data)
        content = soup.find('media:content')

        url = content['url']
        logging.debug (url)

        return self.plugin.set_stream_url(url)

class GlobalNews(CanwestBaseChannel):
    short_name = 'globalnews'
    long_name = 'Global News'
    PID = 'M3FYkz1jcJIVtzmoB4e_ZQfqBdpZSFNM'
    local_channels = [
        ('Global News','z/Global%20News%20Player%20-%20Main'),
        ('Global National','z/Global%20Player%20-%20The%20National%20VC'),
        ('BC', 'z/Global%20BC%20Player%20-%20Video%20Center'),
        ('Calgary', 'z/Global%20CGY%20Player%20-%20Video%20Center'),
        ('Edmonton', 'z/Global%20EDM%20Player%20-%20Video%20Center'),
        ('Lethbridge', 'z/Global%20LTH%20Player%20-%20Video%20Center'),
        ('Maritimes', 'z/Global%20MAR%20Player%20-%20Video%20Center'),
        ('Montreal', 'z/Global%20QC%20Player%20-%20Video%20Center'),
        ('Regina', 'z/Global%20REG%20Player%20-%20Video%20Center'),
        ('Saskatoon', 'z/Global%20SAS%20Player%20-%20Video%20Center'),
        ('Toronto', 'z/Global%20ON%20Player%20-%20Video%20Center'),
        ('Winnipeg', 'z/Global%20WIN%20Player%20-%20Video%20Center'),
    ]

    def get_cache_key(self):
        return "%s-%s" % (self.short_name, self.args.get('local_channel',''))

    def action_browse(self):
        self.PlayerTag = dict(self.local_channels)[self.args['local_channel']]

        if self.args['entry_id'] is None:
            return CanwestBaseChannel.action_root(self)
        return CanwestBaseChannel.action_browse(self)


    def action_root(self):
        for channel, ptag in self.local_channels:
            self.plugin.add_list_item({
                'Title': channel,
                'action': 'browse',
                'channel': self.short_name,
                'entry_id': None,
                'local_channel': channel
            })
        self.plugin.end_list()

    def get_categories_json(self, arg):
        return CanwestBaseChannel.get_categories_json(self, arg) + '&query=CustomText|PlayerTag|' + self.PlayerTag


class HistoryTV(CanwestBaseChannel):
    short_name = 'history'
    long_name = 'History TV'
    PID = 'IX_AH1EK64oFyEbbwbGHX2Y_2A_ca8pk'
    swf_url = 'http://www.history.ca/video/cwp/swf/flvPlayer.swf'

    def get_categories_json(self,arg):
        url = CanwestBaseChannel.get_categories_json(self,arg) + '&query=CustomText|PlayerTag|z/History%20Player%20-%20Video%20Center' #urlencode
        logging.debug('get_categories_json: %s'%url)
        return url


class FoodNetwork(CanwestBaseChannel):
    short_name = 'foodnet'
    long_name = 'The Food Network'
    PID = '6yC6lGVHaVA8oWSm1F9PaIYc9tOTzDqY'
    #swf_url = 'http://webdata.globaltv.com/global/canwestPlayer/swf/4.1/flvPlayer.swf'

    def get_categories_json(self,arg):
        url = CanwestBaseChannel.get_categories_json(self,arg) + '&query=CustomText|PlayerTag|z/FOODNET%20Player%20-%20Video%20Centre' #urlencode
        logging.debug('get_categories_json: %s'%url)
        return url


class HGTV(CanwestBaseChannel):
    short_name = 'hgtv'
    long_name = 'HGTV.ca'
    PID = 'HmHUZlCuIXO_ymAAPiwCpTCNZ3iIF1EG'
    #swf_url = 'http://www.hgtv.ca/includes/cwp/swf/flvPlayer.swf'

    def get_categories_json(self,arg):
        url = CanwestBaseChannel.get_categories_json(self,arg) + '&query=CustomText|PlayerTag|z/HGTVNEWVC%20-%20New%20Video%20Center' #urlencode
        logging.debug('get_categories_json: %s'%url)
        return url



class Showcase(CanwestBaseChannel):
    short_name = 'showcase'
    long_name = 'Showcase'
    PID = 'sx9rVurvXUY4nOXBoB2_AdD1BionOoPy'
    swf_url = 'http://www.showcase.ca/sharedassets/static/video/swf/flvPlayer.swf  swfvfy=true'
    root_depth = 2
    def get_categories_json(self,arg):
        url = CanwestBaseChannel.get_categories_json(self,arg) + '&query=CustomText|PlayerTag|z/Showcase%20Video%20Centre' #urlencode
        logging.debug('get_categories_json: %s'%url)
        return url




class SliceTV(CanwestBaseChannel):
    short_name = 'slice'
    long_name = 'Slice TV'
    PID = 'EJZUqE_dB8XeUUgiJBDE37WER48uEQCY'
    swf_url = 'http://www.slice.ca/includes/vc_20/swf/flvPlayer.swf'

    def get_categories_json(self,arg):
        url = CanwestBaseChannel.get_categories_json(self,arg) + '&query=CustomText|PlayerTag|z/SLICENEWVC%20-%20New%20Video%20Center' #urlencode
        logging.debug('get_categories_json: %s'%url)
        return url


class TVTropolis(CanwestBaseChannel):
    short_name = 'tvtropolis'
    long_name = 'TVtropolis'
    PID = '3i9zvO0c6HSlP7Fz848a0DvzBM0jUWcC'
    #swf_url = 'http://www.tvtropolis.com/swf/cwp/flvPlayer.swf'

    def get_categories_json(self, arg=None):
        url = CanwestBaseChannel.get_categories_json(self) + '&query=CustomText|PlayerTag|z/TVTropolis%20Player%20-%20Video%20Center' #urlencode
        logging.debug('get_categories_json: %s'%url)
        return url


class diyNet(CanwestBaseChannel):
    short_name = 'diynet'
    long_name = 'The DIY Network'
    PID = 'FgLJftQA35gBSx3kKPM46ZVvhP6JxTYt'
    #swf_url = 'http://www.diy.ca/Includes/cwp/swf/flvPlayer.swf'

    def get_categories_json(self,arg):
        url = CanwestBaseChannel.get_categories_json(self,arg) + '&query=CustomText|PlayerTag|z/DIY%20Network%20-%20Video%20Centre' #urlencode
        logging.debug('get_categories_json: %s'%url)
        return url
