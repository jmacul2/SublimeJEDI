import sublime
import sublime_plugin

try:
    from SublimeJEDI.sublime_jedi import (get_script, JediEnvMixin,
                                          get_current_location)
except ImportError:
    from sublime_jedi import get_script, JediEnvMixin, get_current_location

from jedi.api import NotFoundError


def related_names(view):
    script = get_script(view, get_current_location(view))
    try:
        related_names = script.usages()
    except NotFoundError:
        return []
    return filter(lambda x: not x.in_builtin_module(), related_names)


class BaseLookUpJediCommand(JediEnvMixin):
    def is_enabled(self):
        """ check if we can run the command """
        location = get_current_location(self.view)
        return self.view.match_selector(location,
                                        "source.python - string - comment")

    def _jump_to_in_window(self, filename, line_number=None, column_number=None):
        """ Opens a new window and jumps to declaration if possible

            :param filename: string or int
            :param line_number: int
            :param column_number: int
        """
        active_window = self.view.window()

        # If the file was selected from a drop down list
        if isinstance(filename, int):
            if filename == -1:  # cancelled
                return
            filename, line_number, column_number = self.options_map[filename]
        active_window.open_file('%s:%s:%s' % (filename, line_number or 0,
                                column_number or 0), sublime.ENCODED_POSITION)

    def _window_quick_panel_open_window(self, options):
        """ Shows the active `sublime.Window` quickpanel (dropdown) for
            user selection.

            :param option: list of `jedi.api_classes.BasDefinition`
        """
        options = list(options)
        active_window = self.view.window()

        # Map the filenames to line and column numbers
        self.options_map = dict((i, (o.module_path, o.line, o.column))
                                for i, o in enumerate(options))

        # Show the user a selection of filenames
        active_window.show_quick_panel(
            [self.prepare_option(o) for o in options],
            self._jump_to_in_window
        )

    def prepare_option(self, option):
        """ prepare option to display out in quick panel """
        raise NotImplementedError(
            "{} require `prepare_option` definition".format(self.__class__)
        )


class SublimeJediGoto(BaseLookUpJediCommand, sublime_plugin.TextCommand):
    """ go to object definition """
    def run(self, edit):
        with self.env:
            script = get_script(self.view, get_current_location(self.view))

            try:
                defns = script.goto_assignments()
            except NotFoundError:
                return
            else:
                self.handle_definitions(defns)

    def handle_definitions(self, defns):
        # filter out builtin
        defns = [i for i in defns if not i.in_builtin_module()]
        if not defns:
            return False
        if len(defns) == 1:
            defn = defns[0]
            self._jump_to_in_window(defn.module_path, defn.line, defn.column)
        else:
            self._window_quick_panel_open_window(defns)

    def prepare_option(self, option):
        return self.prepare_definition(option)

    def prepare_definition(self, option):
        return option.module_path


class SublimeJediFindUsages(BaseLookUpJediCommand, sublime_plugin.TextCommand):
    """ find object usages """
    def run(self, edit):
        usages = self.find_usages()
        if usages:
            self._window_quick_panel_open_window(usages)

    def find_usages(self):
        with self.env:
            return related_names(self.view)

    def prepare_option(self, option):
        return self.prepare_related_name(option)

    def prepare_related_name(self, option):
        return [option.module_path,
                "line: %d column: %d" % (option.line, option.column)]
