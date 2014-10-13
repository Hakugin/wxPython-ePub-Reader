

#---------------------------------------------------------------------
# Basic ePub reader written in Python, using wxPython for the GUI
# Author: Michael Stover
#
# Status: Work in Progress
# To-Do:
#    - Add function that places images into memory
#    - Add function for placing CSS files into memory
#    - Add function that "fixes" links so that they point to memory
#    - Re-add "Day/Night" mode
#    - Add Text Size adjustments
#    - Add Help/About
#    - "Prettify" Toolbar icons
#---------------------------------------------------------------------

import os
import sys
import wx
import wx.html
import _worker

class HtmlWindow(wx.html.HtmlWindow):
    '''Subclass of wx.html.HtmlWindow. Will allow for users to
    click to internal chapter links and skip to desired chapter,
    or open external links in default browser.'''
    def __init__(self, parent, *arg, **kw):
        '''Constructor.'''
        wx.html.HtmlWindow.__init__(self, parent, *arg, **kw)
        if "gtk2" in wx.PlatformInfo:
            self.SetStandardFonts()
        self.parent = parent
        self.PrimeFrame = wx.GetTopLevelParent(self.parent)

    def OnLinkClicked(self, link):
        '''Override default behavior and perform basic check on
        the link clicked. Attempt to load links in default browser.'''
        clicked = link.GetHref()
        if clicked.startswith('http') or clicked.startswith('www'):
            wx.LaunchDefaultBrowser(link.GetHref())
        else:
            pass

class MainFrame(wx.Frame):
    def __init__(self, parent=None, *arg, **kw):
        '''Constructor for initialization of gui, variables and
        MemoryFSHandler'''
        super(MainFrame, self).__init__(parent, *arg, **kw)

        self.panel = wx.Panel(self, -1)


        self.epubFile = []
        self.epubBookTitle = []
        self.epubInfo = {}
        self.theBook = []
        self.epubImages = []
        self.epubContents = []
        self.epubChapters = []
        self.epubBookmark = {}
        self.nightMode = False
        self.currentSection = 0

        
      # Set the filesystem handler
        wx.FileSystem.AddHandler(wx.MemoryFSHandler())

      # Set up our htmlWin object
        self.htmlWin = HtmlWindow(self.panel)

        self.TopSizer = wx.BoxSizer(wx.VERTICAL)
        self.TopSizer.Add(self.htmlWin, 1, wx.EXPAND|wx.ALL, 5)

        self.panel.SetSizerAndFit(self.TopSizer)
        self.SetSize((650,400))

        self.onInitTB()

    def onInitTB(self):
        '''Initialize the Toolbar.'''
        self.toolBar = self.CreateToolBar(
                    style=wx.TB_NODIVIDER
        )

        self.toolBar.AddSeparator()

        toolOpen = self.toolBar.AddLabelTool(wx.ID_ANY, 'Open Book',
            wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN))

        self.toolBar.AddSeparator()
        self.toolBar.AddSeparator()

        toolHome = self.toolBar.AddLabelTool(wx.ID_ANY, 'Front Page',
            wx.ArtProvider.GetBitmap(wx.ART_GO_HOME))

        self.toolBar.AddSeparator()
        toolBack = self.toolBar.AddLabelTool(wx.ID_ANY, 'Back',
            wx.ArtProvider.GetBitmap(wx.ART_GO_BACK))

        toolNext = self.toolBar.AddLabelTool(wx.ID_ANY, 'Next',
            wx.ArtProvider.GetBitmap(wx.ART_GO_FORWARD))

        self.toolBar.AddStretchableSpace()

        self.toolBar.Realize()

        self.Bind(wx.EVT_TOOL, self.onSelectEpub, toolOpen)
        self.Bind(wx.EVT_TOOL, self.onPageHome, toolHome)
        self.Bind(wx.EVT_TOOL, self.onPageNext, toolNext)
        self.Bind(wx.EVT_TOOL, self.onPageBack, toolBack)

    def OnReset(self):
        '''Reset variables for next book, includes removing
        previous images from memory.'''
        for image in self.epubImages:
            wx.MemoryFSHandler.RemoveFile(image)
        self.epubChapters = []
        self.currentSection = 0

    def onSelectEpub(self, event):
        '''Open FileDialog to select epub file.'''
        wildcard = 'ePub File (*.epub)|*.epub'
        dlg = wx.FileDialog(self, 'Choose a file',
                '', '', wildcard, wx.FD_OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.OnReset()
            self.epubFile = os.path.join(
                dlg.GetDirectory(),
                dlg.GetFilename()
            )
            self.onLoadEpub(self.epubFile)
        dlg.Destroy()

    def onLoadEpub(self, inFile):
        '''Function to open epub and run various processing
        functions on it.'''
        self.theBook = _worker.open_epub(inFile)
        content_soup = _worker.get_epub_content_soup(self.theBook)
        self.epubImages, self.epubText, epubCss = _worker.get_epub_content_lists(content_soup)
        self.epubInfo = _worker.get_epub_general_info(content_soup)
        self.onLoadImgsToMem(self.theBook)
        self.epubBookTitle = self.epubInfo['title']
        self.SetTitle('Reading: %s, by: %s' % (self.epubBookTitle, self.epubInfo['creator']))
        for chapter in self.epubText:
            raw_page = _worker.get_epub_section(self.theBook, chapter)
            new_page = _worker.clean_convert_links(raw_page)
            self.epubChapters.append(new_page)
        self.onLoadPages()

    def onLoadImgsToMem(self, epub_file):
        for image in self.epubImages:
            im_img = _worker.preprocess_image(epub_file, image)
            new_image = wx.EmptyImage(im_img.size[0],im_img.size[1])
            new_image.SetData(im_img.convert("RGB").tostring())
            finalImg = wx.BitmapFromImage(new_image)
            wx.MemoryFSHandler.AddFile(image, finalImg, wx.BITMAP_TYPE_BMP)

    def onLoadPages(self):
        '''Load page into htmlWin.'''
        self.htmlWin.SetPage(self.epubChapters[0])

    def onPageHome(self, event):
        '''Sets the current page back to the beginning of the book.'''
        self.currentSection = 0
        content = self.epubChapters[self.currentSection]
        self.htmlWin.SetPage(content)

    def onPageNext(self, event):
        '''Change to next ePub section / chapter. This needs completed.'''
        if self.currentSection < len(self.epubText)-1:
            self.currentSection += 1
            content = self.epubChapters[self.currentSection]
            self.htmlWin.SetPage(content)
        else:
            dlg = wx.MessageBox('We cannot go further than the end of the book!',
                'ERROR: End of the line!', wx.OK|wx.ICON_HAND)
            event.Skip()

    def onPageBack(self, event):
        '''Change to previous ePub section / chapter. This needs completed.'''
        if self.currentSection > 0:
            self.currentSection -= 1
            content = self.epubChapters[self.currentSection]
            self.htmlWin.SetPage(content)
        else:
            dlg = wx.MessageBox('We cannot go further than the start of the book!',
                'ERROR: Front Page Reached!', wx.OK|wx.ICON_HAND)
            event.Skip()

    def onQuit(self, event):
        '''Close the application'''
        self.Close()

    def onLoadCSSToMem(self, epub_file):
        '''Load CCS pages to memory.'''
      # Needs implemented
        pass

def RunApp():
    '''Initialize wxApp, set primary frame and run MainLoop'''
    app = wx.App(False)
    frame = MainFrame(title='ePub Reader')
    frame.Show()
    app.MainLoop()

if __name__ == '__main__':
    ''''''
    RunApp()
