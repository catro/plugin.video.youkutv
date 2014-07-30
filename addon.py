# -*- coding: utf-8 -*-
# default.py

import xbmcgui, xbmcaddon, xbmc
import json, sys, urllib, urllib2, gzip, StringIO, re, os, time
try:
   import StorageServer
except:
   import storageserverdummy as StorageServer

__addonid__ = "plugin.video.youkutv"
__addon__ = xbmcaddon.Addon(id=__addonid__)
__cwd__ = __addon__.getAddonInfo('path')
__profile__    = xbmc.translatePath( __addon__.getAddonInfo('profile') )
__resource__   = xbmc.translatePath( os.path.join( __cwd__, 'resources', 'lib' ) )
sys.path.append (__resource__)
cache = StorageServer.StorageServer(__addonid__, 87600)
HOST='http://tv.api.3g.youku.com/'
IDS='pid=0dd34e6431923a46&guid=46a51fe8d8e37731535bade1e6b8ae96&gdid=dab5d487f39cab341ead7b2aa90f9caf&ver=2.3.0'
Navigation=['首页', '频道', '排行']
ContentID=[520, 560, 580]
ChannelData={'97': {'icon': 'channel_tv_icon.png', 'title': '电视剧'},\
             '669': {'icon': 'channel_child_icon.png', 'title': '少儿'},\
             '96': {'icon': 'channel_movie_icon.png', 'title': '电影'},\
             '100': {'icon': 'channel_anime_icon.png', 'title': '动漫'},\
             '85': {'icon': 'channel_variety_icon.png', 'title': '综艺'},\
             '84': {'icon': 'channel_documentary_icon.png', 'title': '纪录片'},\
             '87': {'icon': 'channel_education_icon.png', 'title': '教育'},\
             }


ACTION_MOVE_LEFT      = 1
ACTION_MOVE_RIGHT     = 2
ACTION_MOVE_UP        = 3
ACTION_MOVE_DOWN      = 4
ACTION_PAGE_UP        = 5
ACTION_PAGE_DOWN      = 6
ACTION_SELECT_ITEM    = 7
ACTION_HIGHLIGHT_ITEM = 8
ACTION_PARENT_DIR_OLD = 9
ACTION_PARENT_DIR     = 92
ACTION_PREVIOUS_MENU  = 10
ACTION_SHOW_INFO      = 11
ACTION_PAUSE          = 12
ACTION_STOP           = 13
ACTION_NEXT_ITEM      = 14
ACTION_PREV_ITEM      = 15
ACTION_SHOW_GUI       = 18
ACTION_PLAYER_PLAY    = 79
ACTION_MOUSE_LEFT_CLICK = 100
ACTION_MOUSE_MOVE     = 107
ACTION_CONTEXT_MENU   = 117


class BaseWindow(xbmcgui.WindowXML):
    def __init__( self, *args, **kwargs):
        self.session = None
        self.oldWindow = None
        self.busyCount = 0
        xbmcgui.WindowXML.__init__( self )

    def doClose(self):
        self.session.window = self.oldWindow
        self.close()
        
    def onInit(self):
        if self.session:
            self.session.window = self
        else:
            try:
                self.session = VstSession(self)
            except:
                self.close()
        self.setSessionWindow()
        
        
    def onFocus( self, controlId ):
        self.controlId = controlId
        
    def setSessionWindow(self):
        try:
            self.oldWindow = self.session.window
        except:
            self.oldWindow=self
        self.session.window = self
        
    def onAction(self,action):
        if action.getId() == ACTION_PARENT_DIR or action.getId() == ACTION_PREVIOUS_MENU:
            if xbmc.Player().isPlaying():
                xbmc.Player().stop()
            self.doClose()
        else:
            return False

    def showBusy(self):
        if self.busyCount > 0:
            self.busyCount += 1
        else:
            self.busyCount = 1
            xbmc.executebuiltin("ActivateWindow(busydialog)")


    def hideBusy(self):
        if self.busyCount > 0:
            self.busyCount -= 1
        if self.busyCount == 0:
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )

        return True


class MainWindow(BaseWindow):
    def __init__( self, *args, **kwargs):
        self.navInited = False
        self.mainInited = False
        self.channelInited = False
        BaseWindow.__init__(self, args, kwargs)


    def onInit(self):
        BaseWindow.onInit(self)

        self.showBusy()
        
        self.initMain()
        self.initChannelTop()
        self.initNavigation()

        self.hideBusy()


    def initNavigation(self):
        if self.navInited:
            return

        for Id in ContentID[1:]:
            self.getControl(Id).setVisible(False)

        for item in Navigation:
            listitem = xbmcgui.ListItem(label=item)
            self.getControl(510).addItem(listitem)

        self.selectedNavigation = 0
        self.getControl(510).getListItem(0).select(True)
        self.setFocusId(510)

        self.navInited = True

    
    def initMain(self):
        if self.mainInited:
            return

        data = GetHttpData(HOST + 'tv/main?' + IDS)
        data = json.loads(data)
        if not data['status']:
            return
        if data['status'] != 'success':
            return

        for item in data['results']['m1']:
            listitem = xbmcgui.ListItem(label=item['title'], thumbnailImage=item['image'])
            setProperties(listitem, item)
            self.getControl(521).addItem(listitem)
            
        for item in data['results']['m2']:
            listitem = xbmcgui.ListItem(label=item['title'], thumbnailImage=item['big_vertical_image'])
            setProperties(listitem, item)
            self.getControl(522).addItem(listitem)
            
        item = data['results']['m3'][0]
        listitem = xbmcgui.ListItem(label=item['title'], thumbnailImage=item['big_horizontal_image'])
        setProperties(listitem, item)
        self.getControl(524).addItem(listitem)        
            
        for item in data['results']['m3'][1:]:
            listitem = xbmcgui.ListItem(label=item['title'], thumbnailImage=item['big_vertical_image'])
            setProperties(listitem, item)
            self.getControl(525).addItem(listitem)
            
        item = data['results']['m4'][0]
        listitem = xbmcgui.ListItem(label=item['title'], thumbnailImage=item['big_horizontal_image'])
        setProperties(listitem, item)
        self.getControl(527).addItem(listitem)        
            
        for item in data['results']['m4'][1:]:
            listitem = xbmcgui.ListItem(label=item['title'], thumbnailImage=item['big_vertical_image'])
            setProperties(listitem, item)
            self.getControl(528).addItem(listitem)

        self.mainInited = True
            

    def initChannelTop(self):
        if self.channelInited:
            return

        data = GetHttpData(HOST + 'tv/main/top?' + IDS)
        data = json.loads(data)
        if not data['status']:
            return
        if data['status'] != 'success':
            return

        #Channel
        for i in range(0, len(data['results']['channel']), 2):
            item = data['results']['channel'][i]
            listitem = xbmcgui.ListItem(label=item['title'], thumbnailImage=item['image'])
            setProperties(listitem, item)
            self.getControl(560).addItem(listitem)

        for i in range(1, len(data['results']['channel']), 2):
            item = data['results']['channel'][i]
            listitem = xbmcgui.ListItem(label=item['title'], thumbnailImage=item['image'])
            setProperties(listitem, item)
            self.getControl(560).addItem(listitem)

        #Top
        for item in data['results']['top']:
            listitem = xbmcgui.ListItem(label=item['title'], thumbnailImage=item['image'])
            setProperties(listitem, item)
            self.getControl(580).addItem(listitem)

        self.channelInited = True
        

    def onClick( self, controlId ):
        if controlId == 510:
            self.updateNavigation()
        else:
            item = self.getControl(controlId).getSelectedItem()
            if item.getProperty('mtype') == 'show':
                openWindow('detail', self.session, sdata=item.getProperty('showid'))
            elif item.getProperty('mtype') == 'channel':
                openWindow('channel', self.session, sdata=item.getProperty('cid'))
            elif item.getProperty('mtype') == 'all_videos':
                openWindow('other', self.session)
            elif item.getProperty('mtype') == 'favor':
                openWindow('favor', self.session)
            elif item.getProperty('mtype') == 'history':
                openWindow('history', self.session)
            elif item.getProperty('mtype') == 'search':
                openWindow('search', self.session)
            else:
                xbmcgui.Dialog().ok('提示框', '此功能暂未实现，尽请期待')


    def onAction(self, action):
        BaseWindow.onAction(self, action)
        #if action.getId() == ACTION_MOVE_LEFT or action.getId() == ACTION_MOVE_RIGHT or action.getId() == ACTION_MOUSE_MOVE:
        if action.getId() == ACTION_MOVE_LEFT or action.getId() == ACTION_MOVE_RIGHT:
            self.updateNavigation()


    def updateNavigation(self):
        if self.getFocusId() == 510:
            if self.selectedNavigation != self.getControl(510).getSelectedPosition():
                #Disable old selection
                self.getControl(510).getListItem(self.selectedNavigation).select(False)
                self.getControl(ContentID[self.selectedNavigation]).setEnabled(False)
                self.getControl(ContentID[self.selectedNavigation]).setVisible(False)

                #Enable new selection
                self.selectedNavigation = self.getControl(510).getSelectedPosition()
                self.getControl(ContentID[self.selectedNavigation]).setEnabled(True)
                self.getControl(ContentID[self.selectedNavigation]).setVisible(True)
                self.getControl(510).getSelectedItem().select(True)


class ChannelWindow(BaseWindow):
    def __init__( self, *args, **kwargs):
        self.subInited = False
        self.conInited = False
        self.urlArgs = {'pz':'100', 'pg':'1', 'filter':''}
        self.sdata = kwargs.get('sdata')
        BaseWindow.__init__(self, args, kwargs)

        
    def onInit(self):
        BaseWindow.onInit(self)

        self.showBusy()

        self.initSubChannel()
        self.initContent()

        self.hideBusy()

        
    def initSubChannel(self):
        if self.subInited:
            return

        #Title
        channel=ChannelData[self.sdata]
        self.getControl(601).setImage(channel['icon'])
        self.getControl(602).setLabel(channel['title'])

        #Catagory
        data = GetHttpData(HOST + 'tv/v2_0/childchannel/list?' + IDS + '&cid=' + self.sdata)
        data = json.loads(data)
        if not data['status']:
            return
        if data['status'] != 'success':
            return


        #Add hot except child channel
        listitem = xbmcgui.ListItem(label='热播')
        self.getControl(610).addItem(listitem)

        for item in data['results']['result']:
            listitem = xbmcgui.ListItem(label=item['sub_channel_title'])
            setProperties(listitem, item)
            self.getControl(610).addItem(listitem)

        self.selectedNavigation = 0
        self.getControl(610).getListItem(0).select(True)
        self.setFocusId(610)

        self.subInited = True


    def initContent(self):
        if self.conInited:
            return

        self.urlArgs['pg'] = '1'
        self.getControl(620).reset()
        self.updateContent()
            
        self.conInited = True


    def updateContent(self):
        self.showBusy()

        url = HOST + 'layout/smarttv/item_list?' + IDS + '&cid=' + self.sdata
        for k in self.urlArgs:
            url = url + '&' + k + '=' + urllib.quote_plus(self.urlArgs[k])

        data = GetHttpData(url)
        data = json.loads(data)
        if not data['status']:
            self.hideBusy()
            return
        if data['status'] != 'success':
            self.hideBusy()
            return

        for item in data['results']:
            listitem = xbmcgui.ListItem(label=item['showname'], label2=item['stripe_bottom'], thumbnailImage=item['show_vthumburl_hd'])
            setProperties(listitem, item)
            self.getControl(620).addItem(listitem)

        self.hideBusy()


    def updateSelection(self):
        if self.getFocusId() == 610:
            if self.selectedNavigation != self.getControl(610).getSelectedPosition():
                #Disable old selection
                self.getControl(610).getListItem(self.selectedNavigation).select(False)
                #Enable new selection
                self.selectedNavigation = self.getControl(610).getSelectedPosition()
                self.getControl(610).getSelectedItem().select(True)
        

    def onClick( self, controlId ):
        if controlId == 610:
            self.urlArgs['filter'] = getProperty(self.getControl(610).getSelectedItem(), 'filter')

            self.updateSelection()

            self.conInited = False
            self.initContent()
            self.setFocusId(620)
        else:
            item = self.getControl(controlId).getSelectedItem()
            if item.getProperty('type') == 'show':
                openWindow('detail', self.session, sdata=item.getProperty('showid'))
                #play(item.getProperty('videoid'))
            else:
                xbmcgui.Dialog().ok('提示框', '此功能暂未实现，尽请期待')


    def onAction(self, action):
        BaseWindow.onAction(self, action)
        #if action.getId() == ACTION_MOVE_DOWN and self.getFocusId() == 620:
        if self.getFocusId() == 620:
            oldPos = self.getControl(620).getSelectedPosition()
            total = self.getControl(620).size()
            if total - oldPos <= 10:
                pg = int(self.urlArgs['pg']) + 1
                self.urlArgs['pg'] = str(pg)
                self.updateContent()
                self.getControl(620).selectItem(oldPos)
                                

class OtherWindow(BaseWindow):
    def __init__( self, *args, **kwargs):
        self.subInited = False
        self.typeInited = False
        self.conInited = False
        self.urlArgs = {'pz':'100', 'pg':'1', 'cid':'', 'ob':'2'}
        BaseWindow.__init__(self, args, kwargs)

        
    def onInit(self):
        BaseWindow.onInit(self)

        self.showBusy()

        self.initType()
        self.initSubChannel()
        self.initContent()

        self.hideBusy()

        
    def initType(self):
        if self.typeInited:
            return
            
        listitem = xbmcgui.ListItem(label='最新上线')
        self.getControl(903).addItem(listitem)
        listitem = xbmcgui.ListItem(label='最多播放')
        self.getControl(903).addItem(listitem)
        self.getControl(903).getListItem(1).select(True)
    
        self.typeInited = True
        
        
    def initSubChannel(self):
        if self.subInited:
            return

        #Title
        self.getControl(901).setImage('channel_member_icon.png')
        self.getControl(902).setLabel('其它')

        #Catagory
        data = GetHttpData(HOST + 'openapi-wireless/layout/smarttv/channellist?' + IDS)
        data = json.loads(data)
        if not data['status']:
            return
        if data['status'] != 'success':
            return

        for item in data['results']:
            listitem = xbmcgui.ListItem(label=item['title'])
            setProperties(listitem, item)
            self.getControl(910).addItem(listitem)

        self.selectedNavigation = 0
        self.getControl(910).getListItem(0).select(True)
        self.setFocusId(910)
        self.urlArgs['cid'] = getProperty(self.getControl(910).getListItem(0), 'cid')

        self.subInited = True


    def initContent(self):
        if self.conInited:
            return

        self.urlArgs['pg'] = '1'
        self.getControl(920).reset()
        self.updateContent()
            
        self.conInited = True


    def updateContent(self):
        self.showBusy()

        url = HOST + 'layout/smarttv/item_list?' + IDS
        for k in self.urlArgs:
            url = url + '&' + k + '=' + urllib.quote_plus(self.urlArgs[k])

        data = GetHttpData(url)
        data = json.loads(data)
        if not data['status']:
            self.hideBusy()
            return
        if data['status'] != 'success':
            self.hideBusy()
            return

        for item in data['results']:
            if item.has_key('show_thumburl_hd'):
                listitem = xbmcgui.ListItem(label=item['showname'], label2=item['duration'], thumbnailImage=item['show_thumburl_hd'])
            else:
                listitem = xbmcgui.ListItem(label=item['showname'], label2=item['duration'], thumbnailImage=item['show_thumburl'])
            setProperties(listitem, item)
            self.getControl(920).addItem(listitem)

        self.hideBusy()


    def updateSelection(self):
        if self.getFocusId() == 910:
            if self.selectedNavigation != self.getControl(910).getSelectedPosition():
                #Disable old selection
                self.getControl(910).getListItem(self.selectedNavigation).select(False)
                #Enable new selection
                self.selectedNavigation = self.getControl(910).getSelectedPosition()
                self.getControl(910).getSelectedItem().select(True)
        

    def onClick( self, controlId ):
        if controlId == 910:
            self.urlArgs['cid'] = getProperty(self.getControl(910).getSelectedItem(), 'cid')

            self.updateSelection()

            self.conInited = False
            self.initContent()
            self.setFocusId(920)
        elif controlId == 903:
            if self.getControl(903).getSelectedItem().isSelected() == False:
                self.getControl(903).getListItem(int(self.urlArgs['ob']) - 1).select(False)
                self.urlArgs['ob'] = str(self.getControl(903).getSelectedPosition() + 1)
                self.getControl(903).getSelectedItem().select(True)
                self.conInited = False
                self.initContent()
                self.setFocusId(920)
        else:
            item = self.getControl(controlId).getSelectedItem()
            if item.getProperty('type') == 'show':
                openWindow('detail', self.session, sdata=item.getProperty('tid'))
            elif item.getProperty('type') == 'video':
                play(item.getProperty('tid'))
            else:
                xbmcgui.Dialog().ok('提示框', '此功能暂未实现，尽请期待')


    def onAction(self, action):
        BaseWindow.onAction(self, action)
        #if action.getId() == ACTION_MOVE_DOWN and self.getFocusId() == 920:
        if self.getFocusId() == 920:
            oldPos = self.getControl(920).getSelectedPosition()
            total = self.getControl(920).size()
            if total - oldPos <= 10:
                pg = int(self.urlArgs['pg']) + 1
                self.urlArgs['pg'] = str(pg)
                self.updateContent()
                self.getControl(920).selectItem(oldPos)
                                                

class ResultWindow(BaseWindow):
    def __init__( self, *args, **kwargs):
        self.filterInited = False
        self.typeInited = False
        self.conInited = False
        self.showInited = False
        self.selectAll = True
        self.selectDuration = 0
        self.selectOrder = 0
        self.sdata = kwargs.get('sdata')
        self.urlArgs = {'pz':'20', 'pg':'1', 'seconds':'0', 'seconds_end': '0', 'ob':'0'}
        BaseWindow.__init__(self, args, kwargs)

        
    def onInit(self):
        BaseWindow.onInit(self)

        self.showBusy()

        self.initType()
        self.initFilter()
        self.initContent()
        self.initShow()

        self.hideBusy()

        
    def initType(self):
        if self.typeInited:
            return
            
        listitem = xbmcgui.ListItem(label='节目')
        self.getControl(1304).addItem(listitem)
        listitem = xbmcgui.ListItem(label='视频')
        self.getControl(1304).addItem(listitem)
        self.getControl(1304).getListItem(1).select(True)
    
        self.typeInited = True
        
        
    def initFilter(self):
        if self.filterInited:
            return

        #Title
        self.getControl(1301).setLabel('搜索结果')
        self.getControl(1302).setLabel('时长')
        self.getControl(1303).setLabel('排序')

        self.getControl(1310).reset()
        listitem = xbmcgui.ListItem(label='全部结果')
        self.getControl(1310).addItem(listitem)

        #Catagory
        data = GetHttpData(HOST + 'layout/android3_0/searchfilters?' + IDS)
        data = json.loads(data)
        if not data['status']:
            return
        if data['status'] != 'success':
            return

        for item in data['results']['duration']:
            listitem = xbmcgui.ListItem(label=item['title'])
            setProperties(listitem, item)
            self.getControl(1311).addItem(listitem)

        for item in data['results']['order']:
            listitem = xbmcgui.ListItem(label=item['title'])
            setProperties(listitem, item)
            self.getControl(1312).addItem(listitem)

        self.setFocusId(1310)
        self.getControl(1310).getSelectedItem().select(True)
        self.selectAll = True
        self.selectDuration = 0
        self.selectOrder = 0

        self.filterInited = True


    def initContent(self):
        if self.conInited:
            return

        self.urlArgs['pg'] = '1'
        self.getControl(1322).reset()
        if self.getControl(1304).getListItem(0).isSelected():
            self.getControl(1321).setVisible(True)
            self.getControl(1322).setVisible(False)
        else:
            self.getControl(1321).setVisible(False)
            self.getControl(1322).setVisible(True)
        self.updateContent()
            
        self.conInited = True


    def initShow(self):
        if self.showInited:
            return

        url = HOST + 'layout/smarttv/showsearch?copyright_status=1&video_type=1&keyword=' + urllib.quote_plus(self.sdata) + '&' + IDS

        data = GetHttpData(url)
        data = json.loads(data)
        if not data['status']:
            return
        if data['status'] != 'success':
            return

        for item in data['results']:
            if item.has_key('show_vthumburl_hd'):
                listitem = xbmcgui.ListItem(label=item['showname'], thumbnailImage=item['show_vthumburl_hd'])
            else:
                listitem = xbmcgui.ListItem(label=item['showname'], thumbnailImage=item['show_vthumburl'])
            setProperties(listitem, item)
            self.getControl(1321).addItem(listitem)

        self.showInited = True


    def updateContent(self):
        self.showBusy()

        url = HOST + 'openapi-wireless/videos/search/' + urllib.quote_plus(self.sdata) + '?' + IDS
        for k in self.urlArgs:
            url = url + '&' + k + '=' + urllib.quote_plus(self.urlArgs[k])

        data = GetHttpData(url)
        data = json.loads(data)
        if not data['status']:
            self.hideBusy()
            return
        if data['status'] != 'success':
            self.hideBusy()
            return

        for item in data['results']:
            if item.has_key('img_hd'):
                listitem = xbmcgui.ListItem(label=item['title'], label2=item['duration'], thumbnailImage=item['img_hd'])
            else:
                listitem = xbmcgui.ListItem(label=item['title'], label2=item['duration'], thumbnailImage=item['img'])
            setProperties(listitem, item)
            self.getControl(1322).addItem(listitem)

        self.hideBusy()


    def updateSelection(self, Id):
        if Id == 1310:
            self.getControl(1310).getSelectedItem().select(True)
            self.getControl(1311).getListItem(self.selectDuration).select(False)
            self.getControl(1312).getListItem(self.selectOrder).select(False)
            self.selectAll = True
            self.urlArgs['seconds'] = '0'
            self.urlArgs['seconds_end'] = '0'
            self.urlArgs['ob'] = '0'
        elif Id == 1311:
            self.getControl(1311).getListItem(self.selectDuration).select(False)
            self.selectDuration = self.getControl(1311).getSelectedPosition()
            self.getControl(1311).getListItem(self.selectDuration).select(True)
            if self.selectAll == True:
                self.selectAll = False
                self.getControl(1310).getSelectedItem().select(False)
            value = getProperty(self.getControl(1311).getListItem(self.selectDuration), "value")
            try:
                self.urlArgs['seconds'] = value.split('-')[0]
                self.urlArgs['seconds_end'] = value.split('-')[1]
            except:
                pass
        elif Id == 1312:
            self.getControl(1312).getListItem(self.selectOrder).select(False)
            self.selectOrder = self.getControl(1312).getSelectedPosition()
            self.getControl(1312).getListItem(self.selectOrder).select(True)
            if self.selectAll == True:
                self.selectAll = False
                self.getControl(1310).getSelectedItem().select(False)
            self.urlArgs['ob'] = getProperty(self.getControl(1312).getListItem(self.selectOrder), "value")
        

    def onClick( self, controlId ):
        if controlId == 1310 or controlId == 1311 or controlId == 1312:

            self.updateSelection(controlId)

            self.conInited = False
            self.initContent()
            self.setFocusId(1320)
        elif controlId == 1304:
            if self.getControl(1304).getSelectedPosition() == 0:
                self.getControl(1304).getListItem(0).select(True)
                self.getControl(1304).getListItem(1).select(False)
            else:
                self.getControl(1304).getListItem(0).select(False)
                self.getControl(1304).getListItem(1).select(True)

            if self.getControl(1304).getListItem(0).isSelected():
                self.getControl(1321).setVisible(True)
                self.getControl(1322).setVisible(False)
            else:
                self.getControl(1321).setVisible(False)
                self.getControl(1322).setVisible(True)
        elif controlId == 1321:
            item = self.getControl(controlId).getSelectedItem()
            openWindow('detail', self.session, sdata=item.getProperty('showid'))
        elif controlId == 1322:
            item = self.getControl(controlId).getSelectedItem()
            play(item.getProperty('videoid'))
        else:
            xbmcgui.Dialog().ok('提示框', '此功能暂未实现，尽请期待')


    def onAction(self, action):
        BaseWindow.onAction(self, action)
        #if action.getId() == ACTION_MOVE_DOWN and self.getFocusId() == 1322:
        if self.getFocusId() == 1322:
            oldPos = self.getControl(1322).getSelectedPosition()
            total = self.getControl(1322).size()
            if total - oldPos <= 10:
                pg = int(self.urlArgs['pg']) + 1
                self.urlArgs['pg'] = str(pg)
                self.updateContent()
                self.getControl(1322).selectItem(oldPos)
                                                

class SearchWindow(BaseWindow):
    def __init__( self, *args, **kwargs):
        self.subInited = False
        self.conInited = False
        self.inputs = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        self.keywords = ''
        BaseWindow.__init__(self, args, kwargs)

        
    def onInit(self):
        BaseWindow.onInit(self)
        self.initSubChannel()
        self.initContent()

        
    def initSubChannel(self):
        if self.subInited:
            return

        self.getControl(1201).setLabel('中文')
        self.getControl(1202).setLabel('空格')
        self.getControl(1203).setLabel('清空')
        self.getControl(1204).setLabel('退格')
        self.getControl(1205).setLabel('搜索')

        for ch in self.inputs:
            listitem = xbmcgui.ListItem(label=ch)
            self.getControl(1210).addItem(listitem)

        self.subInited = True


    def initContent(self):
        if self.conInited:
            return

        if len(self.keywords) == 0:
            self.getControl(1212).setLabel('大家都在搜:')
            self.getControl(1211).setLabel('[COLOR=grey]输入搜索内容[/COLOR]')
        else:
            self.getControl(1212).setLabel('猜你想搜:')
            self.getControl(1211).setLabel(self.keywords)

        self.getControl(1220).reset()
        self.updateContent()
            
        self.conInited = True


    def updateContent(self):
        self.showBusy()

        if len(self.keywords) == 0:
            data = GetHttpData(HOST + 'openapi-wireless/keywords/recommend?' + IDS)
            title_key = 'title'
        else:
            data = GetHttpData(HOST + 'openapi-wireless/keywords/suggest?' + IDS + '&keywords=' + urllib.quote_plus(self.keywords))
            title_key = 'keyword'

        data = json.loads(data)
        if not data['status']:
            self.hideBusy()
            return
        if data['status'] != 'success':
            self.hideBusy()
            return

        for item in data['results']:
            listitem = xbmcgui.ListItem(label=item[title_key])
            self.getControl(1220).addItem(listitem)

        self.hideBusy()


    def onClick( self, controlId ):
        if controlId == 1210:
            ch = self.inputs[self.getControl(1210).getSelectedPosition()]
            self.keywords = self.keywords + ch
        elif controlId == 1201:
            return
        elif controlId == 1202:
            self.keywords = self.keywords + ' '
        elif controlId == 1203:
            self.keywords = ''
        elif controlId == 1204:
            self.keywords = self.keywords[:-1]
        elif controlId == 1205:
            if len(self.keywords) == 0:
                self.getControl(1211).setLabel('[COLOR=grey]搜索内容不能为空[/COLOR]')
                return
            else:
                openWindow('result', self.session, sdata=self.keywords)
        elif controlId == 1220:
            openWindow('result', self.session, sdata=self.getControl(1220).getSelectedItem().getLabel())
        else:
            xbmcgui.Dialog().ok('提示框', '此功能暂未实现，尽请期待')
            return
 
        self.conInited = False
        self.initContent()
                                

class FavorWindow(BaseWindow):
    def __init__( self, *args, **kwargs):
        self.subInited = False
        self.conInited = False
        BaseWindow.__init__(self, args, kwargs)

        
    def onInit(self):
        BaseWindow.onInit(self)
        self.initSubChannel()
        self.initContent()

        
    def initSubChannel(self):
        if self.subInited:
            return

        #Title
        self.getControl(1001).setImage('icon_my_collect.png')
        self.getControl(1002).setLabel('收藏')

        #Catagory
        listitem = xbmcgui.ListItem(label='节目')
        self.getControl(1010).addItem(listitem)
        listitem = xbmcgui.ListItem(label='视频')
        self.getControl(1010).addItem(listitem)

        self.selectedNavigation = 0
        self.getControl(1010).getListItem(0).select(True)
        self.setFocusId(1010)

        self.subInited = True


    def initContent(self):
        if self.conInited:
            return

        self.getControl(1020).reset()
        if self.selectedNavigation == 0:
            self.updateContent()
            
        self.conInited = True


    def updateContent(self):
        try:
            ret = eval(cache.get('favor'))
        except:
            ret = None
        if ret == None:
            return
        ret = sorted(ret.values(), lambda y,x: cmp(x['addedTime'], y['addedTime']))
        for item in ret:
            listitem = xbmcgui.ListItem(label=item['title'], thumbnailImage=item['img'])
            setProperties(listitem, item)
            self.getControl(1020).addItem(listitem)


    def updateSelection(self):
        if self.getFocusId() == 1010:
            if self.selectedNavigation != self.getControl(1010).getSelectedPosition():
                #Disable old selection
                self.getControl(1010).getListItem(self.selectedNavigation).select(False)
                #Enable new selection
                self.selectedNavigation = self.getControl(1010).getSelectedPosition()
                self.getControl(1010).getSelectedItem().select(True)
        

    def onClick( self, controlId ):
        if controlId == 1010:
            self.updateSelection()
            self.conInited = False
            self.initContent()
            if self.getControl(1020).size() > 0:
                self.setFocusId(1020)
        elif controlId == 1020:
            try:
                retOld = cache.get('favor')
            except:
                retOld = None
            showid = self.getControl(1020).getSelectedItem().getProperty('showid')
            openWindow('detail', self.session, sdata=showid)
            try:
                ret = cache.get('favor')
            except:
                ret = None

            if retOld != ret:
                self.conInited = False
                self.initContent()
                self.setFocusId(1020)
        else:
            xbmcgui.Dialog().ok('提示框', '此功能暂未实现，尽请期待')
 

class HistoryWindow(BaseWindow):
    def __init__( self, *args, **kwargs):
        self.subInited = False
        self.conInited = False
        BaseWindow.__init__(self, args, kwargs)

        
    def onInit(self):
        BaseWindow.onInit(self)
        self.initSubChannel()
        self.initContent()

        
    def initSubChannel(self):
        if self.subInited:
            return

        #Title
        self.getControl(1101).setImage('icon_my_history.png')
        self.getControl(1102).setLabel('历史')
 
        self.subInited = True


    def initContent(self):
        if self.conInited:
            return

        self.getControl(1110).reset()
        self.updateContent()
        self.setFocusId(1110)
            
        self.conInited = True


    def updateContent(self):
        try:
            ret = eval(cache.get('history'))
        except:
            ret = None
        if ret == None:
            return
        ret = sorted(ret.values(), lambda y,x: cmp(x['addedTime'], y['addedTime']))
        for item in ret:
            listitem = xbmcgui.ListItem(label=item['title'], label2=item['vid'], thumbnailImage=item['logo'])
            self.getControl(1110).addItem(listitem)


    def onClick( self, controlId ):
        play(self.getControl(1110).getSelectedItem().getLabel2())
        self.conInited = False
        self.initContent()
        self.setFocusId(1110)

            
class DetailWindow(BaseWindow):
    def __init__( self, *args, **kwargs):
        self.inited = False
        self.sdata = kwargs.get('sdata')
        self.pdata = None
        BaseWindow.__init__(self, args, kwargs)

        
    def onInit(self):
        BaseWindow.onInit(self)
        self.init()

        
    def init(self):
        if self.inited:
            return

        self.showBusy()

        data = GetHttpData(HOST + 'layout/smarttv/play/detail?' + IDS + '&id=' + self.sdata)
        data = json.loads(data)
        if not data['status']:
            self.hideBusy()
            return
        if data['status'] != 'success':
            self.hideBusy()
            return            
        
        data = data['detail']
        self.pdata = data
        self.getControl(701).setImage(data['img'])
        setLabel(self.getControl(702), data, 'title', '', '', '', '')
        setLabel(self.getControl(703), data, 'reputation', '0.0', '', u'分', '')
        setLabel(self.getControl(704), data, 'showdate', u'未知', u'上映：', '', '')
        setLabel(self.getControl(705), data, 'stripe_bottom', u'未知', u'集数：', '', '')
        setLabel(self.getControl(706), data, 'area', u'未知', u'地区：', '', '/')
        setLabel(self.getControl(707), data, 'genre', u'未知', u'类型：', '', '/')
        setLabel(self.getControl(708), data, 'director', u'未知', u'导演：', '', '/')
        setLabel(self.getControl(709), data, 'performer', u'未知', u'演员：', '', '/')
        self.getControl(710).setLabel('简介：')
        setLabel(self.getControl(711), data, 'desc', '', '', '', '')

        self.getControl(721).setLabel('选集')
        added = True
        try:
            ret = eval(cache.get('favor'))
        except:
            ret = None
        if ret != None:
            if ret.has_key(self.sdata):
                added = False
        if added:
            self.getControl(722).setLabel('收藏')
        else:
            self.getControl(722).setLabel('已收藏')
        self.getControl(723).setLabel(getNumber(data, 'total_vv'))
        self.getControl(724).setLabel(getNumber(data, 'total_fav'))

        try:
            if data['episode_total'] == '1':
                #self.getControl(721).setVisible(False)
                self.getControl(721).setEnabled(False)
        except:
            pass

        self.getControl(740).reset()

        data = GetHttpData(HOST + 'common/shows/relate?' + IDS + '&id=' + self.sdata)
        data = json.loads(data)
        if not data['status']:
            self.hideBusy()
            return
        if data['status'] != 'success':
            self.hideBusy()
            return            

        for item in data['results']:
            listitem = xbmcgui.ListItem(label=item['showname'], thumbnailImage=item['show_vthumburl'])
            setProperties(listitem, item)
            self.getControl(740).addItem(listitem)

        self.hideBusy()

        self.inited = True
        

    def onClick( self, controlId ):
        if controlId == 740:
            self.sdata = getProperty(self.getControl(740).getSelectedItem(), 'showid')
            self.inited = False
            self.init()
        elif controlId == 720:
            play(self.pdata['videoid'])
        elif controlId == 721:
            openWindow('select', self.session, sdata=self.sdata)
        elif controlId == 722:
            self.changeFavor()
        else:
            xbmcgui.Dialog().ok('提示框', '此功能暂未实现，尽请期待')


    def changeFavor(self):
        try:
            ret = eval(cache.get('favor'))
        except:
            ret = None
        if ret == None:
            self.pdata['addedTime'] = time.time()
            cache.set('favor', repr({self.sdata:  self.pdata}))
            self.getControl(722).setLabel('已收藏')
        elif ret.has_key(self.sdata):
            del(ret[self.sdata])
            cache.set('favor', repr(ret))
            self.getControl(722).setLabel('收藏')
        else:
            self.pdata['addedTime'] = time.time()
            ret[self.sdata] = self.pdata
            cache.set('favor', repr(ret))
            self.getControl(722).setLabel('已收藏')
            
            
class SelectWindow(xbmcgui.WindowXMLDialog):
    def __init__( self, *args, **kwargs):
        self.inited = False
        self.sdata = kwargs.get('sdata')
        self.pdata = None
        self.selected = 0
        self.session = None
        self.oldWindow = None
        xbmcgui.WindowXML.__init__( self )
        

    def doClose(self):
        self.session.window = self.oldWindow
        self.close()

        
    def onInit(self):
        if self.session:
            self.session.window = self
        else:
            try:
                self.session = VstSession(self)
            except:
                self.close()
        self.setSessionWindow()

        xbmc.executebuiltin("ActivateWindow(busydialog)")
        self.init()
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        
        
    def onFocus( self, controlId ):
        self.controlId = controlId
        
        
    def setSessionWindow(self):
        try:
            self.oldWindow = self.session.window
        except:
            self.oldWindow=self
        self.session.window = self        

        
    def init(self):
        if self.inited:
            return

        self.getControl(801).setLabel('剧集:')

        data = GetHttpData(HOST + 'layout/smarttv/shows/' + self.sdata + '/series?' + IDS)
        data = json.loads(data)
        if not data['status']:
            return
        if data['status'] != 'success':
            return            

        data = data['results']
        data.sort(lambda x,y: cmp(x['video_stage'], y['video_stage']))
        self.pdata = data

        total = len(data)
        for i in range(1, total + 1, 20):
            start = str(i)
            if i + 19 < total:
                end = str(i + 19)
            else:
                end = str(total)
            listitem = xbmcgui.ListItem(label=start + '-' + end)
            listitem.setProperty('start', start)
            listitem.setProperty('end', end)
            self.getControl(810).addItem(listitem)

        self.selectRange(0)
        self.setFocusId(820)

        self.inited = True


    def selectRange(self, index):
        self.getControl(810).getListItem(self.selected).select(False)
        item = self.getControl(810).getListItem(index)
        item.select(True)
        self.selected = index

        self.getControl(820).reset()
        start = int(item.getProperty('start'))
        end = int(item.getProperty('end'))

        fromTitle = False
        if len(self.pdata) > 1:
            if self.pdata[0]['title'] != self.pdata[1]['title']:
                lastSpace = 0
                for i in range(1, len(self.pdata[0]['title'])):
                    if self.pdata[0]['title'][:i] != self.pdata[1]['title'][:i]:
                        break
                    if self.pdata[0]['title'][i - 1] == ' ':
                        lastSpace = i
                if lastSpace > 0:
                    trim = self.pdata[0]['title'][:(i-1)]
                else:
                    trim = self.pdata[0]['title'][:lastSpace]
                fromTitle = True
        for i in range(start, end + 1):
            if fromTitle == True:
                listitem = xbmcgui.ListItem(label=self.pdata[i-1]['title'].replace(trim, ''))
            else:
                listitem = xbmcgui.ListItem(label=str(self.pdata[i-1]['video_stage']))
            self.getControl(820).addItem(listitem)
        

    def onClick( self, controlId ):
        if controlId == 810:
            self.selectRange(self.getControl(810).getSelectedPosition())
        else:
            self.doClose()
            play(self.pdata[self.getControl(820).getSelectedPosition()]['videoid'])


    def onAction(self, action):
        if action.getId() == ACTION_PARENT_DIR or action.getId() == ACTION_PREVIOUS_MENU:
            self.doClose()
        elif self.getFocusId() == 810:
            if action.getId() == ACTION_MOVE_LEFT or action.getId() == ACTION_MOVE_RIGHT:
                self.selectRange(self.getControl(810).getSelectedPosition())

        
class VstSession:
    def __init__(self,window=None):
        self.window = window
        
    def removeCRLF(self,text):
        return " ".join(text.split())
        
    def makeAscii(self,name):
        return name.encode('ascii','replace')
        
    def closeWindow(self):
        self.window.doClose()
            
    def clearSetting(self,key):
        __addon__.setSetting(key,'')
        
    def setSetting(self,key,value):
        __addon__.setSetting(key,value and ENCODE(value) or '')
        
    def getSetting(self,key,default=None):
        setting = __addon__.getSetting(key)
        if not setting: return default
        if type(default) == type(0):
            return int(float(setting))
        elif isinstance(default,bool):
            return setting == 'true'
        return setting


def getNumber(data, k):
    try:
        s = data[k]
        s = s.replace(',', '')
        n = float(s)
        if(n > 100000000):
            f = n / 100000000
            return str("%.1f"%f) + u'亿次'
        elif(n > 10000):
            f = n / 10000
            return str("%.1f"%f) + u'万次'
        else:
            return str(n)
    except:
        return '0次'

        
def setLabel(c, data, k, default, pre, app, sep):
    try:
        label = data[k]
        c.setLabel(pre + sep.join(label) + app)
    except:
        try:
            c.setLabel(pre + str(sep.join(label)) + app) 
        except:
            try:
                c.setLabel(pre + unicode(sep.join(label)) + app) 
            except:
                c.setLabel(pre + default + app)   


def setProperties(listitem, item):
    for k in item:
        try:     
            listitem.setProperty(k, item[k])  
        except:
            try:
                listitem.setProperty(k, str(item[k]))
            except:
                listitem.setProperty(k, unicode(item[k]))


def getProperty(item, key):
    try:
        value = item.getProperty(key)
    except:
        value = ''

    return value


def play(vid):
    try:
        xbmc.executebuiltin("ActivateWindow(busydialog)")
        stypes = ['hd2', 'mp4', 'flv']
        moviesurl="http://v.youku.com/player/getPlayList/VideoIDS/{0}/ctype/12/ev/1".format(vid)
        result = GetHttpData(moviesurl)
        movinfo = json.loads(result.replace('\r\n',''))
        movdat = movinfo['data'][0]
        streamfids = movdat['streamfileids']
        video_id = movdat['videoid']
        stype = 'flv'

        if len(streamfids) > 1:
            selstypes = [v for v in stypes if v in streamfids]
            stype = selstypes[0]

        if False:
            #Use m3u8 url
            playurl = r'http://v.youku.com/player/getM3U8/vid/' + vid + r'/type/' + stype + '/video.m3u8'
            listitem=xbmcgui.ListItem()
            listitem.setInfo(type="Video",infoLabels={"Title":movdat['title']})
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            xbmc.Player().play(playurl, listitem)
        else:
            #Get url from www.flvcd.com
            flvcdurl='http://www.flvcd.com/parse.php?format=super&kw='+urllib.quote_plus('http://v.youku.com/v_show/id_'+vid+'.html')
            result = GetHttpData(flvcdurl)
            foobars = re.compile('(http://k.youku.com/.*)"\starget', re.M).findall(result)
            if len(foobars) < 1:
                xbmcgui.Dialog().ok('提示框', '解析地址异常，无法播放')
                return
            playlist = xbmc.PlayList(1)
            playlist.clear()
            for i in range(0,len(foobars)):
                title =movdat['title'] + u" - 第"+str(i+1)+"/"+str(len(foobars)) + u"节"
                listitem=xbmcgui.ListItem(title)
                listitem.setInfo(type="Video",infoLabels={"Title":title})
                playlist.add(foobars[i], listitem)
            xbmc.executebuiltin( "Dialog.Close(busydialog)" )
            xbmc.Player().play(playlist)
    except:
        xbmc.executebuiltin( "Dialog.Close(busydialog)" )
        xbmcgui.Dialog().ok('提示框', '解析地址异常，无法播放')
        return

    #Add to history
    data = {'addedTime': time.time(), \
            'title': movdat['title'], \
            'vid': vid, \
            'logo': movdat['logo']}
    try:
        ret = eval(cache.get('history'))
    except:
        ret = None
    if ret == None:
        cache.set('history', repr({vid: data}))
    elif ret.has_key(vid):
        old = ret[vid]
        for key in old.keys():
            if data.has_key(key) == False:
                data[key] = old[key]
        ret[vid] = data
        cache.set('history', repr(ret))
    else:
        ret[vid] = data
        cache.set('history', repr(ret))


def openWindow(window_name,session=None,**kwargs):
    windowFile = '%s.xml' % window_name
    if window_name == 'main':
        w = MainWindow(windowFile , __cwd__, "Default",session=session,**kwargs)
    elif window_name == 'channel':
        w = ChannelWindow(windowFile , __cwd__, "Default",session=session,**kwargs)
    elif window_name == 'detail':
        w = DetailWindow(windowFile , __cwd__, "Default",session=session,**kwargs)
    elif window_name == 'select':
        w = SelectWindow(windowFile , __cwd__, "Default",session=session,**kwargs)
    elif window_name == 'other':
        w = OtherWindow(windowFile , __cwd__, "Default",session=session,**kwargs)
    elif window_name == 'favor':
        w = FavorWindow(windowFile , __cwd__, "Default",session=session,**kwargs)
    elif window_name == 'history':
        w = HistoryWindow(windowFile , __cwd__, "Default",session=session,**kwargs)
    elif window_name == 'search':
        w = SearchWindow(windowFile , __cwd__, "Default",session=session,**kwargs)
    elif window_name == 'result':
        w = ResultWindow(windowFile , __cwd__, "Default",session=session,**kwargs)
    else:
        w = BaseWindow(windowFile , __cwd__, "Default",session=session,**kwargs)
    w.doModal()            
    del w


def GetHttpData(url):
    print ('Frech: ' + url)
    try:
        req = urllib2.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) {0}{1}'.
                       format('AppleWebKit/537.36 (KHTML, like Gecko) ',
                              'Chrome/28.0.1500.71 Safari/537.36'))
        req.add_header('Accept-encoding', 'gzip')
        response = urllib2.urlopen(req)
        httpdata = response.read()
        if response.headers.get('content-encoding', None) == 'gzip':
            httpdata = gzip.GzipFile(fileobj=StringIO.StringIO(httpdata)).read()
        response.close()
        match = re.compile('encodingt=(.+?)"').findall(httpdata)
        if len(match)<=0:
            match = re.compile('meta charset="(.+?)"').findall(httpdata)
        if len(match)>0:
            charset = match[0].lower()
            if (charset != 'utf-8') and (charset != 'utf8'):
                httpdata = unicode(httpdata, charset).encode('utf8')
    except:
        httpdata = '{"status": "Fail"}'

    return httpdata


if __name__ == '__main__':
    openWindow('main')
