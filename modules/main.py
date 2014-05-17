# -*- coding: UTF-8 -*-
#
#       main.py
#
#       Copyright 2009-2014 Giuseppe Penone <giuspen@gmail.com>
#
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 3 of the License, or
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

import gtk, gobject
import dbus
import dbus.service
import dbus.mainloop.glib
import sys, os, gettext
import __builtin__
msg_server_to_core = {'f':0, 'p':""}
__builtin__.msg_server_to_core = msg_server_to_core
import cons, core


class CherryTreeObject(dbus.service.Object):

    @dbus.service.method("com.giuspen.CherryTreeInterface",
                         in_signature='s', out_signature='s')
    def Send(self, in_message):
        if len(in_message) < 4 or in_message[:4] != "ct*=":
            print "bad in_message =", in_message
            return ""
        sep_pos = in_message.find("\x03")
        filepath = filepath_fix(in_message[4:sep_pos] if sep_pos != -1 else in_message[4:])
        node_name = in_message[sep_pos+1:] if sep_pos != -1 else ""
        msg_server_to_core['p'] = filepath
        msg_server_to_core['n'] = node_name
        msg_server_to_core['f'] = 1
        return "okz"


class CherryTreeHandler():
    def __init__(self, args, lang_str):
        self.lang_str = lang_str
        self.running_windows = []
        self.systray_active = False
        self.window_open_new(filepath_fix(args.filepath), args.node, True, True if args.filepath else False)
        self.server_check_timer_id = gobject.timeout_add(1000, self.server_periodic_check) # 1 sec

    def window_open_new(self, filepath, node_name, is_startup, is_arg):
        """Open a new top level Window"""
        window = core.CherryTree(self.lang_str, filepath, node_name, self, is_startup, is_arg)
        self.running_windows.append(window)
        #print self.running_windows

    def on_window_destroy_event(self, widget):
        """Before close the application (from the window top right X)..."""
        #print self.running_windows
        for i, runn_win in enumerate(self.running_windows):
            if runn_win.window == widget:
                print "win destroy: runn_win found with id", i
                break
        else:
            print "win destroy: runn_win not found"
            i = -1
        self.running_windows.pop(i)
        if not self.running_windows: gtk.main_quit()

    def server_periodic_check(self):
        """Check Whether the server posted messages"""
        #print "check '%s'" % msg_server_to_core['f']
        if msg_server_to_core['f']:
            msg_server_to_core['f'] = 0
            # 0) debug
            for i, runn_win in enumerate(self.running_windows):
                print "already running '%s' - '%s'" % (runn_win.file_dir, runn_win.file_name)
            # 1) check for opened window with same filepath
            for i, runn_win in enumerate(self.running_windows):
                if msg_server_to_core['p']\
                and runn_win.file_name\
                and msg_server_to_core['p'] == os.path.join(runn_win.file_dir, runn_win.file_name):
                    print "1 rise existing '%s'" % msg_server_to_core['p']
                    runn_win.window.present()
                    node_name = msg_server_to_core['n']
                    if node_name:
                        node_name_iter = runn_win.get_tree_iter_from_node_name(node_name, use_content=False)
                        if not node_name_iter:
                            node_name_iter = runn_win.get_tree_iter_from_node_name(node_name, use_content=True)
                        if node_name_iter:
                            runn_win.treeview_safe_set_cursor(node_name_iter)
                            runn_win.sourceview.grab_focus()
                    break
            else:
                # 2) check for opened window with empty path
                for i, runn_win in enumerate(self.running_windows):
                    if not runn_win.file_name:
                        print "2 rise existing '%s'" % msg_server_to_core['p']
                        runn_win.window.present()
                        runn_win.file_startup_load(msg_server_to_core['p'], "")
                        break
                else:
                    # 3) check for opened window hidden (systray) in case there's no filepath (run from launcher)
                    just_run_new_win = True
                    if not msg_server_to_core['p']:
                        for i, runn_win in enumerate(self.running_windows):
                            if not runn_win.window.get_property(cons.STR_VISIBLE):
                                print "3 rise existing hidden in systray"
                                runn_win.window.present()
                                just_run_new_win = False
                                break
                    if just_run_new_win:
                        # 4) run new window
                        print "4 run '%s'" % msg_server_to_core['p']
                        self.window_open_new(msg_server_to_core['p'], msg_server_to_core['n'], False, False)
        return True # this way we keep the timer alive


def initializations():
    """Initializations"""
    if not os.path.isdir(os.path.dirname(cons.CONFIG_DIR)): os.mkdir(os.path.dirname(cons.CONFIG_DIR))
    if not os.path.isdir(cons.CONFIG_DIR): os.mkdir(cons.CONFIG_DIR)
    if hasattr(sys, 'frozen'):
        import warnings
        warnings.filterwarnings(cons.STR_IGNORE)
    if not cons.IS_WIN_OS:
        try:
            # change process name
            import ctypes, ctypes.util
            libc = ctypes.cdll.LoadLibrary(ctypes.util.find_library("libc"))
            libc.prctl(15, cons.APP_NAME, 0, 0, 0)
        except:
            print "libc.prctl not available, the process name will be python and not cherrytree"
    import locale
    locale.setlocale(locale.LC_ALL, '')
    try:
        # change locale text domain
        locale.bindtextdomain(cons.APP_NAME, cons.LOCALE_PATH)
        locale.bind_textdomain_codeset(cons.APP_NAME, cons.STR_UTF8)
    except:
        try:
            from ctypes import cdll
            libintl = cdll.intl
            libintl.bindtextdomain(cons.APP_NAME, cons.LOCALE_PATH)
            libintl.bind_textdomain_codeset(cons.APP_NAME, cons.STR_UTF8)
        except:
            pass
        try:
            from ctypes import windll
            lcid = windll.kernel32.GetUserDefaultUILanguage()
            os.environ["LANGUAGE"] = cons.MICROSOFT_WINDOWS_LCID_to_ISO_LANG[lcid]
        except:
            pass
    # language installation
    if os.path.isfile(cons.LANG_PATH):
        lang_file_descriptor = file(cons.LANG_PATH, 'r')
        lang_str = lang_file_descriptor.read()
        lang_file_descriptor.close()
        if lang_str != 'default': os.environ["LANGUAGE"] = lang_str
    else: lang_str = 'default'
    try: gettext.translation(cons.APP_NAME, cons.LOCALE_PATH).install()
    except:
        import __builtin__
        def _(transl_str):
            return transl_str
        __builtin__._ = _
    return lang_str


def filepath_fix(filepath):
    """Fix a FilePath to an Absolute Path"""
    if not filepath: return ""
    if not os.path.dirname(filepath): filepath = os.path.join(os.getcwd(), filepath)
    else: filepath = os.path.abspath(filepath)
    return filepath


def main(args):
    """Everything Starts from Here"""
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    session_bus = dbus.SessionBus()
    try:
        # client
        remote_object = session_bus.get_object("com.giuspen.CherryTreeService", "/CherryTreeObject")
        if not args.node: ret_val = remote_object.Send("ct*=%s" % args.filepath)
        else: ret_val = remote_object.Send("ct*=%s\x03%s" % (args.filepath, args.node))
        if ret_val != "okz": raise
    except:
        #raise
        # server + core
        lang_str = initializations()
        name = dbus.service.BusName("com.giuspen.CherryTreeService", session_bus)
        object = CherryTreeObject(session_bus, '/CherryTreeObject')
        CherryTreeHandler(args, lang_str)
        gtk.main() # start the gtk main loop
