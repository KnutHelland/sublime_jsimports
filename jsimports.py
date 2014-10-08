import sublime
import sublime_plugin
import sys
import os
import subprocess

if (sys.version_info[0] == 3):
	from vendor.diff_match_patch.python3.diff_match_patch import diff_match_patch
else:
	from vendor.diff_match_patch.python2.diff_match_patch import diff_match_patch


class MergeException(Exception):
	pass

# from GoSublime
def _merge(view, size, text, edit):
	def ss(start, end):
		return view.substr(sublime.Region(start, end))
	dmp = diff_match_patch()
	diffs = dmp.diff_main(ss(0, size), text)
	dmp.diff_cleanupEfficiency(diffs)
	i = 0
	dirty = False
	for d in diffs:
		k, s = d
		l = len(s)
		if k == 0:
			# match
			l = len(s)
			if ss(i, i+l) != s:
				raise MergeException('mismatch', dirty)
			i += l
		else:
			dirty = True
			if k > 0:
				# insert
				view.insert(edit, i, s)
				i += l
			else:
				# delete
				if ss(i, i+l) != s:
					raise MergeException('mismatch', dirty)
				view.erase(edit, sublime.Region(i, i+l))
	return dirty

# from GoSublime
def merge(view, size, text, edit):
	vs = view.settings()
	ttts = vs.get("translate_tabs_to_spaces")
	vs.set("translate_tabs_to_spaces", False)
	origin_src = view.substr(sublime.Region(0, view.size()))
	if not origin_src.strip():
		return (False, '')

	try:
		dirty = False
		err = ''
		if size < 0:
			size = view.size()
		dirty = _merge(view, size, text, edit)
	except MergeException as ex:
		dirty = True
		err = "Could not merge changes into the buffer, edit aborted: %s" % ex[0]
		view.replace(edit, sublime.Region(0, view.size()), origin_src)
	except Exception as ex:
		err = "where ma bees at?: %s" % ex
	finally:
		vs.set("translate_tabs_to_spaces", ttts)
		return (dirty, err)



class JsimportsCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		vsize = self.view.size()
		src = self.view.substr(sublime.Region(0, vsize))
		if not src.strip():
			return

		tmpName = self.view.file_name() + '_jsimports.js';
		if not tmpName:
			sublime.error_message("Current file has no name. Save it first")
			return

		with open(tmpName, 'w') as f:
			f.write(src)

                node = self.view.settings().get('node_path', '/usr/local/bin/node')
                jsimp = self.view.settings().get('jsimports_path', '/usr/local/bin/jsimports')

		err = ''
		try:
			err = subprocess.check_output([node, jsimp, tmpName, '-w'])
		except FileNotFoundError:
			sublime.error_message("Could not find node and/or jsimports executable")
			os.remove(tmpName)
			return
		except subprocess.CalledProcessError as e:
			sublime.status_message("Got error status code " + str(e))
			
		if err:
			sublime.status_message("Could not run jsimports " + str(err))
			os.remove(tmpName);
			return

		with open(tmpName, 'r') as f:
			content = f.read()

		os.remove(tmpName);

		_, err = merge(self.view, vsize, content, edit)
		if err:
			msg = 'PANIC: Cannot fmt file. Check your source for errors (and maybe undo any changes).'
			sublime.error_message("%s: %s: Merge failure: `%s'" % (DOMAIN, msg, err))


