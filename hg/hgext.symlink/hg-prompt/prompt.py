#!/usr/bin/env python

"""get repository information for use in a shell prompt

Take a string, parse any special variables inside, and output the result.

Useful mostly for putting information about the current repository into
a shell prompt.
"""

from __future__ import with_statement
from os.path import expanduser
import re
import os
import subprocess
from datetime import datetime, timedelta
from os import path
from mercurial import extensions, commands, cmdutil, help
from mercurial.node import hex, short

# `revrange' has been moved into module `scmutil' since v1.9.
try :
    from mercurial import scmutil
    revrange = scmutil.revrange
except :
    revrange = cmdutil.revrange

CACHE_PATH = ".hg/prompt/cache"
CACHE_TIMEOUT = timedelta(minutes=2)

FILTER_ARG = re.compile(r'\|.+\((.*)\)')

# This is kind of a hack and I feel a little bit dirty for doing it.
IGNORE = open('NUL:','w') if subprocess.mswindows else open('/dev/null','w')

# When we need to log
LOG_FILE = expanduser( "~") + "/tmp/prompt.txt"


def _cache_remote(repo, kind, force=False):
    spawnDaemon( repo, 'both', force )
    return

def _with_groups(groups, out):
    out_groups = [groups[0]] + [groups[-1]]

    if any(out_groups) and not all(out_groups):
        print 'Error parsing prompt string.  Mismatched braces?'

    out = out.replace('%', '%%')
    return ("%s" + out + "%s") % (out_groups[0][:-1] if out_groups[0] else '',
                                  out_groups[1][1:] if out_groups[1] else '')

def _get_filter(name, g):
    """Return the filter with the given name, or None if it was not used."""
    matching_filters = filter(lambda s: s and s.startswith('|%s' % name), g)
    if not matching_filters:
        return None

    # Later filters will override earlier ones, for now.
    f = matching_filters[-1]

    return f

def _get_filter_arg(f):
    if not f:
        return None

    args = FILTER_ARG.match(f).groups()
    if args:
        return args[0]
    else:
        return None

def prompt(ui, repo, fs='', **opts):
    """get repository information for use in a shell prompt

    Take a string and output it for use in a shell prompt. You can use
    keywords in curly braces::

        $ hg prompt "currently on {branch}"
        currently on default

    You can also use an extended form of any keyword::

        {optional text here{keyword}more optional text}

    This will expand the inner {keyword} and output it along with the extra
    text only if the {keyword} expands successfully.  This is useful if you
    have a keyword that may not always apply to the current state and you
    have some text that you would like to see only if it is appropriate::

        $ hg prompt "currently at {bookmark}"
        currently at
        $ hg prompt "{currently at {bookmark}}"
        $ hg bookmark my-bookmark
        $ hg prompt "{currently at {bookmark}}"
        currently at my-bookmark

    See 'hg help prompt-keywords' for a list of available keywords.
    """

    def _basename(m):
        return _with_groups(m.groups(), path.basename(repo.root)) if repo.root else ''

    def _bookmark(m):
        try:
            book = extensions.find('bookmarks').current(repo)
        except AttributeError:
            book = getattr(repo, '_bookmarkcurrent', None)
        except KeyError:
            book = getattr(repo, '_bookmarkcurrent', None)
        if book is None:
            book = getattr(repo, '_activebookmark', None)
        if book:
            cur = repo['.'].node()
            if repo._bookmarks[book] == cur:
                return _with_groups(m.groups(), book)
        else:
            return ''

    def _branch(m):
        g = m.groups()

        branch = repo.dirstate.branch()
        quiet = _get_filter('quiet', g)

        out = branch if (not quiet) or (branch != 'default') else ''

        return _with_groups(g, out) if out else ''

    def _closed(m):
        g = m.groups()

        quiet = _get_filter('quiet', g)

        p = repo[None].parents()[0]
        pn = p.node()
        branch = repo.dirstate.branch()
        closed = (p.extra().get('close')
                  and pn in repo.branchheads(branch, closed=True))
        out = 'X' if (not quiet) and closed else ''

        return _with_groups(g, out) if out else ''

    def _count(m):
        g = m.groups()
        query = [g[1][1:]] if g[1] else ['all()']
        return _with_groups(g, str(len(revrange(repo, query))))

    def _node(m):
        g = m.groups()

        parents = repo[None].parents()
        p = 0 if '|merge' not in g else 1
        p = p if len(parents) > p else None

        format = short if '|short' in g else hex

        node = format(parents[p].node()) if p is not None else None
        return _with_groups(g, str(node)) if node else ''

    def _patch(m):
        g = m.groups()

        try:
            extensions.find('mq')
        except KeyError:
            return ''

        q = repo.mq

        if _get_filter('quiet', g) and not len(q.series):
            return ''

        if _get_filter('topindex', g):
            if len(q.applied):
                out = str(len(q.applied) - 1)
            else:
                out = ''
        elif _get_filter('applied', g):
            out = str(len(q.applied))
        elif _get_filter('unapplied', g):
            out = str(len(q.unapplied(repo)))
        elif _get_filter('count', g):
            out = str(len(q.series))
        else:
            out = q.applied[-1].name if q.applied else ''

        return _with_groups(g, out) if out else ''

    def _patches(m):
        g = m.groups()

        try:
            extensions.find('mq')
        except KeyError:
            return ''

        join_filter = _get_filter('join', g)
        join_filter_arg = _get_filter_arg(join_filter)
        sep = join_filter_arg if join_filter else ' -> '

        patches = repo.mq.series
        applied = [p.name for p in repo.mq.applied]
        unapplied = filter(lambda p: p not in applied, patches)

        if _get_filter('hide_applied', g):
            patches = filter(lambda p: p not in applied, patches)
        if _get_filter('hide_unapplied', g):
            patches = filter(lambda p: p not in unapplied, patches)

        if _get_filter('reverse', g):
            patches = reversed(patches)

        pre_applied_filter = _get_filter('pre_applied', g)
        pre_applied_filter_arg = _get_filter_arg(pre_applied_filter)
        post_applied_filter = _get_filter('post_applied', g)
        post_applied_filter_arg = _get_filter_arg(post_applied_filter)

        pre_unapplied_filter = _get_filter('pre_unapplied', g)
        pre_unapplied_filter_arg = _get_filter_arg(pre_unapplied_filter)
        post_unapplied_filter = _get_filter('post_unapplied', g)
        post_unapplied_filter_arg = _get_filter_arg(post_unapplied_filter)

        for n, patch in enumerate(patches):
            if patch in applied:
                if pre_applied_filter:
                    patches[n] = pre_applied_filter_arg + patches[n]
                if post_applied_filter:
                    patches[n] = patches[n] + post_applied_filter_arg
            elif patch in unapplied:
                if pre_unapplied_filter:
                    patches[n] = pre_unapplied_filter_arg + patches[n]
                if post_unapplied_filter:
                    patches[n] = patches[n] + post_unapplied_filter_arg

        return _with_groups(g, sep.join(patches)) if patches else ''

    def _queue(m):
        g = m.groups()

        try:
            extensions.find('mq')
        except KeyError:
            return ''

        q = repo.mq

        out = os.path.basename(q.path)
        if out == 'patches' and not os.path.isdir(q.path):
            out = ''
        elif out.startswith('patches-'):
            out = out[8:]

        return _with_groups(g, out) if out else ''

    def _remote(kind):
        def _r(m):
            g = m.groups()

            cache_dir = path.join(repo.root, CACHE_PATH)
            cache = path.join(cache_dir, kind)
            if not path.isdir(cache_dir):
                os.makedirs(cache_dir)

            cache_exists = path.isfile(cache)

            cache_time = (datetime.fromtimestamp(os.stat(cache).st_mtime)
                          if cache_exists else None)
            if not cache_exists or cache_time < datetime.now() - CACHE_TIMEOUT:
                # Using ".pid" means we don't want to wait for the process to finish...
                #noinspection PyUnusedLocal
                pid = subprocess.Popen(['hg', 'prompt', '--cache-%s' % kind]).pid

            if cache_exists:
                with open(cache) as c:
                    count = len(c.readlines())
                    if g[1]:
                        return _with_groups(g, str(count)) if count else ''
                    else:
                        return _with_groups(g, '') if count else ''
            else:
                return ''
        return _r

    def _rev(m):
        g = m.groups()

        parents = repo[None].parents()
        parent = 0 if '|merge' not in g else 1
        parent = parent if len(parents) > parent else None

        rev = parents[parent].rev() if parent is not None else -1
        return _with_groups(g, str(rev)) if rev >= 0 else ''

    def _root(m):
        return _with_groups(m.groups(), repo.root) if repo.root else ''

    def _status(m):
        from hgext.largefiles import lfutil

        g = m.groups()

        st = repo.status(unknown=True)[:5]
        modified = any(st[:4])
        unknown = len(st[-1]) > 0

        '''
        largefiles break the unknown indicator, need to check that all the unknown files are not actually largefile files
        '''
        if lfutil.islfilesrepo(repo):
            if unknown:
                largefiles = set(lfutil.listlfiles(repo))
                unknown = False if set(st[-1]).issubset(largefiles) else True

        flag = ''
        if '|modified' not in g and '|unknown' not in g:
            flag = '!' if modified else '?' if unknown else ''
        else:
            if '|modified' in g:
                flag += '!' if modified else ''
            if '|unknown' in g:
                flag += '?' if unknown else ''

        return _with_groups(g, flag) if flag else ''

    def _tags(m):
        g = m.groups()

        sep = g[2][1:] if g[2] else ' '
        tags = repo[None].tags()

        quiet = _get_filter('quiet', g)
        if quiet:
            tags = filter(lambda tag: tag != 'tip', tags)

        return _with_groups(g, sep.join(tags)) if tags else ''

    def _task(m):
        try:
            task = extensions.find('tasks').current(repo)
            return _with_groups(m.groups(), task) if task else ''
        except KeyError:
            return ''

    def _tip(m):
        g = m.groups()

        format = short if '|short' in g else hex

        tip = repo[len(repo) - 1]
        rev = tip.rev()
        tip = format(tip.node()) if '|node' in g else tip.rev()

        return _with_groups(g, str(tip)) if rev >= 0 else ''

    def _update(m):
        current_rev = repo[None].parents()[0]

        # Get the tip of the branch for the current branch
        try:
            heads = repo.branchmap()[current_rev.branch()]
            tip = heads[-1]
        except (KeyError, IndexError):
            # We are in an empty repository.

            return ''

        for head in reversed(heads):
            if not repo[head].closesbranch():
                tip = head
                break

        return _with_groups(m.groups(), '^') if current_rev != repo[tip] else ''


    if opts.get("angle_brackets"):
        tag_start = r'\<([^><]*?\<)?'
        tag_end = r'(\>[^><]*?)?>'
        brackets = '<>'
    else:
        tag_start = r'\{([^{}]*?\{)?'
        tag_end = r'(\}[^{}]*?)?\}'
        brackets = '{}'

    patterns = {
        'bookmark': _bookmark,
        'branch(\|quiet)?': _branch,
        'closed(\|quiet)?': _closed,
        'count(\|[^%s]*?)?' % brackets[-1]: _count,
        'node(?:'
            '(\|short)'
            '|(\|merge)'
            ')*': _node,
        'patch(?:'
            '(\|topindex)'
            '|(\|applied)'
            '|(\|unapplied)'
            '|(\|count)'
            '|(\|quiet)'
            ')*': _patch,
        'patches(?:' +
            '(\|join\([^%s]*?\))' % brackets[-1] +
            '|(\|reverse)' +
            '|(\|hide_applied)' +
            '|(\|hide_unapplied)' +
            '|(\|pre_applied\([^%s]*?\))' % brackets[-1] +
            '|(\|post_applied\([^%s]*?\))' % brackets[-1] +
            '|(\|pre_unapplied\([^%s]*?\))' % brackets[-1] +
            '|(\|post_unapplied\([^%s]*?\))' % brackets[-1] +
            ')*': _patches,
        'queue': _queue,
        'rev(\|merge)?': _rev,
        'root': _root,
        'root\|basename': _basename,
        'status(?:'
            '(\|modified)'
            '|(\|unknown)'
            ')*': _status,
        'tags(?:' +
            '(\|quiet)' +
            '|(\|[^%s]*?)' % brackets[-1] +
            ')*': _tags,
        'task': _task,
        'tip(?:'
            '(\|node)'
            '|(\|short)'
            ')*': _tip,
        'update': _update,

        'incoming(\|count)?': _remote('incoming'),
        'outgoing(\|count)?': _remote('outgoing'),
    }

    if opts.get("cache_incoming"):
      _cache_remote(repo, 'incoming')

    if opts.get("cache_outgoing"):
        _cache_remote(repo, 'outgoing')

    for tag, repl in patterns.items():
        fs = re.sub(tag_start + tag + tag_end, repl, fs)
    ui.status(fs)


def _remove_cache(repo, type):
  cache = path.join( repo.root, CACHE_PATH, type )
  if path.isfile( cache ):
    os.remove( cache )

  tmp_cache = cache + '.temp'
  if path.isfile( tmp_cache ):
    os.remove( tmp_cache )


def _pull_with_cache(orig, ui, repo, *args, **opts):
    """Wrap the pull command to delete the incoming cache as well."""
    res = orig(ui, repo, *args, **opts)
    _remove_cache( repo, 'incoming' )
    _cache_remote(repo, 'outgoing')
    return res

def _push_with_cache(orig, ui, repo, *args, **opts):
    """Wrap the push command to delete the outgoing cache as well."""
    res = orig(ui, repo, *args, **opts)
    _remove_cache( repo, 'outgoing' )
    _cache_remote(repo, 'incoming')
    return res

def _commit_with_cache(orig, ui, repo, *args, **opts):
    """Wrap the commit command to update the outgoing cache as well."""
    res = orig(ui, repo, *args, **opts)
    _cache_remote(repo, 'outgoing', True)
    return res

def uisetup(ui):
    extensions.wrapcommand(commands.table, 'pull', _pull_with_cache)
    extensions.wrapcommand(commands.table, 'push', _push_with_cache)
    extensions.wrapcommand(commands.table, 'commit', _commit_with_cache)
    try:
        extensions.wrapcommand(extensions.find("fetch").cmdtable, 'fetch', _pull_with_cache)
    except KeyError:
        pass

cmdtable = {
    "prompt":
    (prompt, [
        ('', 'angle-brackets', None, 'use angle brackets (<>) for keywords'),
        ('', 'cache-incoming', None, 'used internally by hg-prompt'),
        ('', 'cache-outgoing', None, 'used internally by hg-prompt'),
    ],
    'hg prompt STRING')
}
help.helptable += (
    (['prompt-keywords', 'prompt-keywords'], ('Keywords supported by hg-prompt'),
     (r'''hg-prompt currently supports a number of keywords.

Some keywords support filters.  Filters can be chained when it makes
sense to do so.  When in doubt, try it!

bookmark
     Display the current bookmark (requires the bookmarks extension).

branch
     Display the current branch.

     |quiet
         Display the current branch only if it is not the default branch.

closed
     Display `X` if working on a closed branch (i.e. committing now would reopen
     the branch).

count
     Display the number of revisions in the given revset (the revset `all()`
     will be used if none is given).

     See `hg help revsets` for more information.

     |REVSET
         The revset to count.

incoming
     Display nothing, but if the default path contains incoming changesets the
     extra text will be expanded.

     For example: `{incoming changes{incoming}}` will expand to
     `incoming changes` if there are changes, otherwise nothing.

     Checking for incoming changesets is an expensive operation, so `hg-prompt`
     will cache the results in `.hg/prompt/cache/` and refresh them every 15
     minutes.

     |count
         Display the number of incoming changesets (if greater than 0).

node
     Display the (full) changeset hash of the current parent.

     |short
         Display the hash as the short, 12-character form.

     |merge
         Display the hash of the changeset you're merging with.

outgoing
     Display nothing, but if the current repository contains outgoing
     changesets (to default) the extra text will be expanded.

     For example: `{outgoing changes{outgoing}}` will expand to
     `outgoing changes` if there are changes, otherwise nothing.

     Checking for outgoing changesets is an expensive operation, so `hg-prompt`
     will cache the results in `.hg/prompt/cache/` and refresh them every 15
     minutes.

     |count
         Display the number of outgoing changesets (if greater than 0).

patch
     Display the topmost currently-applied patch (requires the mq
     extension).

     |count
         Display the number of patches in the queue.

     |topindex
         Display (zero-based) index of the topmost applied patch in the series
         list (as displayed by :hg:`qtop -v`), or the empty string if no patch
         is applied.

     |applied
         Display the number of currently applied patches in the queue.

     |unapplied
         Display the number of currently unapplied patches in the queue.

     |quiet
         Display a number only if there are any patches in the queue.

patches
     Display a list of the current patches in the queue.  It will look like
     this:

         :::console
         $ hg prompt '{patches}'
         bottom-patch -> middle-patch -> top-patch

     |reverse
         Display the patches in reverse order (i.e. topmost first).

     |hide_applied
         Do not display applied patches.

     |hide_unapplied
         Do not display unapplied patches.

     |join(SEP)
         Display SEP between each patch, instead of the default ` -> `.

     |pre_applied(STRING)
         Display STRING immediately before each applied patch.  Useful for
         adding color codes.

     |post_applied(STRING)
         Display STRING immediately after each applied patch.  Useful for
         resetting color codes.

     |pre_unapplied(STRING)
         Display STRING immediately before each unapplied patch.  Useful for
         adding color codes.

     |post_unapplied(STRING)
         Display STRING immediately after each unapplied patch.  Useful for
         resetting color codes.

queue
     Display the name of the current MQ queue.

rev
     Display the repository-local changeset number of the current parent.

     |merge
         Display the repository-local changeset number of the changeset you're
         merging with.

root
     Display the full path to the root of the current repository, without a
     trailing slash.

     |basename
         Display the directory name of the root of the current repository. For
         example, if the repository is in `/home/u/myrepo` then this keyword
         would expand to `myrepo`.

status
     Display `!` if the repository has any changed/added/removed files,
     otherwise `?` if it has any untracked (but not ignored) files, otherwise
     nothing.

     |modified
         Display `!` if the current repository contains files that have been
         modified, added, removed, or deleted, otherwise nothing.

     |unknown
         Display `?` if the current repository contains untracked files,
         otherwise nothing.

tags
     Display the tags of the current parent, separated by a space.

     |quiet
         Display the tags of the current parent, excluding the tag "tip".

     |SEP
         Display the tags of the current parent, separated by `SEP`.

task
     Display the current task (requires the tasks extension).

tip
     Display the repository-local changeset number of the current tip.

     |node
         Display the (full) changeset hash of the current tip.

     |short
         Display a short form of the changeset hash of the current tip (must be
         used with the **|node** filter)

update
     Display `^` if the current parent is not the tip of the current branch,
     otherwise nothing.  In effect, this lets you see if running `hg update`
     would do something.
''')),
)


#myLogger = open( LOG_FILE, 'a+' )

#
# This method is taken from http://stackoverflow.com/questions/972362/spawning-process-from-python
#   which in turn derived it from http://code.activestate.com/recipes/278731/
#
# noinspection PyRedundantParentheses
def spawnDaemon( repo, kind, force ):
  """Spawn a completely detached subprocess (i.e., a daemon).
  """
  #myLogger.write( ' [' + kind + '] spawning\n' )

  # First check if the temp file already exists. If so, how old is it? If it's fairly recent,
  #   then assume another operation is already in progress...
  if kind == 'both':
    inCache = ensureCache( repo, 'incoming', force )
    outCache = ensureCache( repo, 'outgoing', force )

    if inCache is None and outCache is None:
      #myLogger.write( ' [' + kind + '] buh-bye\n' )
      #myLogger.flush()
      #myLogger.close()
      return

    if inCache is None:
      kind = 'outgoing'
      #myLogger.write( ' [' + kind + '] only out!\n' )
    elif outCache is None:
      kind = 'incoming'
      #myLogger.write( ' [' + kind + '] only in!\n' )

  else:
    cache = ensureCache( repo, kind, force )
    if cache is None:
      #myLogger.flush()
      #myLogger.close()
      return

    if kind == 'incoming':
      inCache = cache
    else:
      outCache = cache

  #myLogger.write( ' [' + kind + '] sok...\n')

  # Fork a child process so the parent can exit.  This returns control to
  # the command-line or shell.  It also guarantees that the child will not
  # be a process group leader, since the child receives a new process ID
  # and inherits the parent's process group ID.  This step is required
  # to insure that the next call to os.setsid is successful.
  try:
    pid = os.fork()
  except OSError, e:
    #myLogger.write( ' [' + kind + '] 1st fork error: ' + e.__str__() + '\n' )
    raise RuntimeError( "1st fork failed: %s [%d]" % (e.strerror, e.errno) )
  if pid != 0:
    # parent (calling) process is all done
    #myLogger.write( ' [' + kind + '] forked\n' )
    #myLogger.flush()
    #myLogger.close()
    return

  # To become the session leader of this new session and the process group
  # leader of the new process group, we call os.setsid().  The process is
  # also guaranteed not to have a controlling terminal.
  # detach from controlling terminal (to make child a session-leader)
  #myLogger.write( ' [' + kind + '] becoming session leader...whatever...\n' )
  os.setsid()

  try:
     # Fork a second child and exit immediately to prevent zombies.  This
     # causes the second child process to be orphaned, making the init
     # process responsible for its cleanup.  And, since the first child is
     # a session leader without a controlling terminal, it's possible for
     # it to acquire one by opening a terminal in the future (System V-
     # based systems).  This second fork guarantees that the child is no
     # longer a session leader, preventing the daemon from ever acquiring
     # a controlling terminal.
    pid = os.fork()
  except OSError, e:
    #myLogger.write( ' [' + kind + '] 2nd fork error: ' + e.__str__() + '\n' )
    raise RuntimeError( "2nd fork failed: %s [%d]" % (e.strerror, e.errno) )
  if pid != 0:
    # child process is all done
    #myLogger.write( ' [' + kind + '] child is done\n' )
    #myLogger.flush()
    #myLogger.close()
    os._exit( 0 )

  # grandchild process now non-session-leader, detached from parent
  # grandchild process must now close all open files
  try:
    maxfd = os.sysconf( "SC_OPEN_MAX" )
  except (AttributeError, ValueError):
    maxfd = 1024
  os.closerange(0, maxfd)


  if inCache is not None:
    runForCache( 'incoming', inCache )

  if outCache is not None:
    runForCache( 'outgoing', outCache )



def ensureCache( repo, kind, force ):
  cache = path.join(repo.root, CACHE_PATH, kind)
  #myLogger.writelines( ' [' + kind + '] checking ' + cache + '\n' )

  cache_exists = path.isfile(cache)
  if not cache_exists:
    open(cache, 'w').close()

  c_tmp = cache + '.temp'

  if os.path.exists( c_tmp ):
    created = datetime.fromtimestamp( os.stat( c_tmp ).st_ctime )
    now = datetime.now()
    maxAge = now - CACHE_TIMEOUT
    if ( created > maxAge ) and not force:
      cache = None
    else:
      os.remove( c_tmp )

  #myLogger.write( ' [' + kind + '] ensureCache: ' + cache.__str__( ) + '\n' )
  return cache


def runForCache( kind, cache ):

  #myLogger = open( LOG_FILE, 'a+' )

  c_tmp = cache + '.temp'
  #myLogger.write( ' [' + kind + '] invoking into ' + c_tmp.__str__() + '\n')

  try:
    subprocess.call(['hg', kind, '--quiet'], stdout=file(c_tmp, 'w'), stderr=None)
    #myLogger.write( ' [' + kind + '] renaming ' + c_tmp + ' to ' + cache + '\n' )
    os.rename(c_tmp, cache)
    #myLogger.write( ' [' + kind + '] renamed ' + c_tmp + ' to ' + cache + '\n' )
  except Exception, e:
    # oops, we're cut off from the world, let's just give up
    #myLogger.write( ' [' + kind + '] uh oh...' + e.__str__() + '\n' )
    os.remove(c_tmp)
    os.remove(cache)
    # os._exit( 255 )

  #myLogger.flush()
  #myLogger.close()
