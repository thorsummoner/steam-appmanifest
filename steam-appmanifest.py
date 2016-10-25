#!/usr/bin/env python3
"""
    by dotfloat
    complaints go to dotfloat at gmail dot com

    Running:
    You need to have 'python3' and 'python3-gi' installed.

    On Debian/Ubuntu and derivatives, you have to run this:
    $ sudo apt-get install python3 python3-gi

    On ArchLinux and derivatives:
    $ sudo pacman -S python python-gobject
"""

from gi.repository import Gtk
from xml.etree.ElementTree import ElementTree
import signal
from os import (
    path,
    listdir,
    remove,
)
import textwrap
from os.path import isfile, join
import re
try:
    from urllib import urlopen
except ImportError:
    from urllib.request import urlopen

# Change this to where your SteamApps folder is located.
# The default ('~/.steam/steam/SteamApps') should be valid for all Linux installations.
# "~/.steam/steam" is a symlink to "$XDG_DATA_HOME/Steam" (normally "~/.local/share/Steam")
STEAM_APPS = path.expanduser('~/.steam/steam/steamapps')

class DlgToggleApp(Gtk.Dialog):
    """ Delete Dialog
    """

    def __init__(self, parent, exists, appid, name):
        Gtk.Dialog.__init__(self, "Install appmanifest", parent, 0)
        self.set_default_size(300, 100)

        label0 = Gtk.Label("Install \""+ name +"\"?")
        label1 = Gtk.Label("appmanifest_"+ str(appid) +".acf")

        if exists:
            self.set_title("appmanifest already exists")
            self.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                             "Delete anyway", Gtk.ResponseType.OK)
            label0.set_text("This will just remove the appmanifest file")
            label1.set_text("Use Steam to remove all of \""+ name +"\".")
        else:
            self.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                             "Install", Gtk.ResponseType.OK,)

        self.get_content_area().add(label0)
        self.get_content_area().add(label1)
        self.show_all()

class DlgManual(Gtk.Dialog):
    """ Manual ACF Info Dialog
    """
    def __init__(self, parent):
        Gtk.Dialog.__init__(self, "Manually install appmanifest", parent, 0,
                            ("Cancel", Gtk.ResponseType.CANCEL,
                             "Install", Gtk.ResponseType.OK))

        self.set_default_size(200, 50)

        appidlabel = Gtk.Label("Game AppID:")
        self.appidentry = Gtk.Entry()

        appidhbox = Gtk.HBox()
        appidhbox.pack_start(appidlabel, False, False, True)
        appidhbox.pack_start(self.appidentry, False, False, True)

        instdirlabel = Gtk.Label("Game directory name:")
        self.instdirentry = Gtk.Entry()

        instdirhbox = Gtk.HBox()
        instdirhbox.pack_start(instdirlabel, False, False, True)
        instdirhbox.pack_start(self.instdirentry, False, False, True)

        vbox = Gtk.VBox()
        vbox.pack_start(appidhbox, False, False, True)
        vbox.pack_start(instdirhbox, False, False, True)

        self.get_content_area().add(vbox)
        self.show_all()

class AppManifest(Gtk.Window):
    """ Main App
    """
    @staticmethod
    def main():
        """ Enter GTK Gui Dialog
        """
        signal.signal(signal.SIGINT, signal.SIG_DFL)

        AppManifest()
        Gtk.main()

    def __init__(self):
        Gtk.Window.__init__(self, title="appmanifest.acf Generator")
        self.connect("delete-event", Gtk.main_quit)

        self.set_default_size(480, 300)

        if not path.exists(STEAM_APPS):
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
                                       Gtk.ButtonsType.OK, "Couldn't find a Steam install")
            dialog.format_secondary_text('Looked in "'+ STEAM_APPS +'"')
            dialog.run()
            dialog.destroy()
            exit()

        border_box = Gtk.Box(margin=10)
        self.add(border_box)
        border_box.show()

        vbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            expand=True,
        )

        self._init_inputs(vbox)
        self._init_appid_table(vbox)
        self._init_actions(vbox)

        border_box.add(vbox)
        vbox.show()
        self.show()

    def _init_inputs(self, vbox):
        """ Top bar
        """
        row0_label = Gtk.Label("https://steamcommunity.com/id/")
        self.steamid = Gtk.Entry()
        self.steamid.connect('activate', self.on_refresh)
        self.btn_refresh = Gtk.Button("Refresh")

        self.btn_refresh.connect("clicked", self.on_refresh)

        row0 = Gtk.Box(spacing=6)
        row0.pack_start(row0_label, True, True, 0)
        row0.pack_start(self.steamid, True, True, 0)
        row0.pack_start(self.btn_refresh, True, True, 0)
        vbox.pack_start(row0, False, False, True)
        row0.show_all()

        # second row
        self.infobar = Gtk.InfoBar(
            message_type=Gtk.MessageType.WARNING,
            show_close_button=True,
        )
        self.infobar_label = Gtk.Label()
        self.infobar.get_content_area().add(self.infobar_label)
        self.infobar.connect("response", self.on_infobar_close)

        vbox.pack_start(self.infobar, False, False, 0)

    def _init_appid_table(self, vbox):
        """ AppIds Liststore and Table
        """
        self.game_liststore = Gtk.ListStore(bool, int, str)

        row2_treeview = Gtk.TreeView(model=self.game_liststore)

        row2_renderer_text = Gtk.CellRendererText()
        row2_renderer_check = Gtk.CellRendererToggle()

        row2_col_toggle = Gtk.TreeViewColumn("", row2_renderer_check, active=0)
        row2_col_appid = Gtk.TreeViewColumn("AppID", row2_renderer_text, text=1)
        row2_col_title = Gtk.TreeViewColumn("Title", row2_renderer_text, text=2)

        row2_renderer_check.connect("toggled", self.on_app_toggle)

        row2_treeview.append_column(row2_col_toggle)
        row2_treeview.append_column(row2_col_appid)
        row2_treeview.append_column(row2_col_title)

        frame = Gtk.Frame(shadow_type=Gtk.ShadowType.IN)

        row2 = Gtk.ScrolledWindow()
        row2.set_size_request(200, 400)
        row2.add(row2_treeview)
        frame.add(row2)

        vbox.pack_start(frame, True, True, 0)
        frame.show_all()

    def _init_actions(self, vbox):
        """ ButtonBox
        """
        row3_manual = Gtk.Button("Manual")
        row3_quit = Gtk.Button("Quit")

        row3_manual.connect("clicked", self.on_manual_click)
        row3_quit.connect("clicked", self.on_quit_click)

        row3 = Gtk.ButtonBox(
            orientation=Gtk.Orientation.HORIZONTAL,
            homogeneous=True,
            layout_style=Gtk.ButtonBoxStyle.EDGE,
        )
        row3.pack_start(row3_manual, True, True, 0)
        row3.pack_start(row3_quit, True, True, 0)

        vbox.pack_start(row3, False, False, 0)
        row3.show_all()

    # slots
    def on_refresh(self, _):
        """ Refresh action
        """
        self.btn_refresh.set_sensitive(False)
        self.refresh_appids()
        self.btn_refresh.set_sensitive(True)

    def refresh_appids(self):
        """ Fetch user library
        """
        self.game_liststore.clear()

        if not self.steamid.get_text():
            return

        files = [f for f in listdir(STEAM_APPS) if isfile(join(STEAM_APPS, f))]
        appids = []

        for file_name in files:
            match = re.search(r"appmanifest_([0-9]+).acf", file_name)
            if match:
                appids.append(int(match.groups(1)[0]))

        url = "http://steamcommunity.com/id/"+ self.steamid.get_text() +"/games?tab=all&xml=1"
        html = urlopen(url)
        tree = ElementTree()
        tree.parse(html)
        games_xml = tree.getiterator('game')
        for game in games_xml:
            appid = int(game.find('appID').text)
            name = game.find('name').text
            exists = appid in appids
            self.game_liststore.append([exists, appid, name])

        error = tree.find('error')
        if getattr(error, 'text', False):
            self._infobar_message(error.text)
        else:
            self.infobar.hide()

    def on_app_toggle(self, _, table_path):
        """ Appid Toggle Action
        """
        appid = self.game_liststore[table_path][1]
        name = self.game_liststore[table_path][2]
        exists = self.refresh_single_row(table_path)

        dialog = DlgToggleApp(self, exists, appid, name)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            acf_file = STEAM_APPS + "/appmanifest_"+ str(appid) +".acf"
            if exists:
                remove(acf_file)
            else:
                self.add_game(appid, name)
        dialog.destroy()

        self.refresh_single_row(table_path)

    def on_manual_click(self, _):
        """ Manual ACF Dialog spawner
        """
        dialog = DlgManual(self)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            self.add_game(int(dialog.appidentry.get_text()), dialog.instdirentry.get_text())

        dialog.destroy()

    def on_quit_click(self, _):
        """ Main Quit
        """
        self.destroy()
        Gtk.main_quit()

    def refresh_single_row(self, row):
        """ Update appid entry by row reference
        """
        acf_file = STEAM_APPS + "/appmanifest_"+ str(self.game_liststore[row][1]) +".acf"
        exists = path.isfile(acf_file)

        self.game_liststore[row][0] = exists

        return exists

    def add_game(self, appid, name):
        """ Write ACF file for appid with name
        """
        acf_file = STEAM_APPS + "/appmanifest_"+ str(appid) +".acf"
        file_descriptor = open(acf_file, 'w')
        file_descriptor.write(
            textwrap.dedent('''
                "AppState"
                {{
                \t"appid"\t"{appid}"
                \t"Universe"\t"1"
                \t"installdir"\t"{name}"
                \t"StateFlags"\t"1026"
                }}
            ''').format(appid=appid, name=name)
        )
        file_descriptor.close()
        self._infobar_message("Restart Steam for the changes to take effect.")

    def _infobar_message(self, message):
        """ Display a warning message
        """
        self.infobar_label.set_text(message)
        self.infobar.show_all()
        self.infobar.show()

    @staticmethod
    def on_infobar_close(widget, _):
        """ Allow user to dismis info bar
        """
        widget.hide()

if __name__ == '__main__':
    AppManifest.main()
