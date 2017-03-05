# -*- coding:utf-8 -*-
import os
import time
import tempfile
import shutil
import subprocess
import binascii
import hashlib
import markdown2
import evernote.edam.userstore.constants as UserStoreConstants
from evernote.edam.limits import constants as LimitsConstants
import evernote.edam.notestore.NoteStore as NoteStore
import evernote.edam.type.ttypes as Types

from evernote.api.client import EvernoteClient

# https://sandbox.evernote.com/api/DeveloperToken.action
# https://app.yinxiang.com/api/DeveloperToken.action
auth_token = "your developer token"

if auth_token == "your developer token":
    print "Please fill in your developer token"
    print "To get a developer token, visit " \
        "https://sandbox.evernote.com/api/DeveloperToken.action"
    exit(1)

client = EvernoteClient(service_host='app.yinxiang.com', token=auth_token, sandbox=False)

user_store = client.get_user_store()

version_ok = user_store.checkVersion(
    "Evernote EDAMTest (Python)",
    UserStoreConstants.EDAM_VERSION_MAJOR,
    UserStoreConstants.EDAM_VERSION_MINOR
)
print "my Evernote API version up to date? ", str(version_ok)
print ""
if not version_ok:
    exit(1)

note_store = client.get_note_store()


def make_resource(path, mime):
    body = open(path, 'rb').read()
    md5 = hashlib.md5()
    md5.update(body)
    hash = md5.digest()
    data = Types.Data()
    data.size = len(body)
    data.bodyHash = hash
    data.body = body
    resource = Types.Resource()
    resource.mime = mime
    resource.data = data
    return resource


def create_note(title, notebook,png_path,  markdown_path, html_path):
    """
    `title`: 标题
    `filename`: 文件名
    """
    note = Types.Note()
    note.notebookGuid = notebook.guid
    note.resources = []
    png_resource = make_resource(png_path, "image/png")
    note.resources.append(png_resource)

    if os.path.exists(markdown_path):
        markdown_resource = make_resource(markdown_path, "text/plain")
        note.resources.append(markdown_resource)

    if os.path.exists(html_path):
        html_resource = make_resource(html_path, "text/html")
        note.resources.append(html_resource)

    note.title = title
    note.content = '<?xml version="1.0" encoding="UTF-8"?>'
    note.content += '<!DOCTYPE en-note SYSTEM ' \
        '"http://xml.evernote.com/pub/enml2.dtd">'
    note.content += '<en-note>'
    for resource in note.resources:
        note.content += '<en-media type="' + resource.mime + '" hash="' + binascii.hexlify(resource.data.bodyHash)+ '"/>'
    note.content += '</en-note>'
    return note_store.createNote(note)


def update_note(note, title, png_path, markdown_path, html_path):
    """
    `title`: 标题
    `filename`: 文件名
    """
    note.updated = int(time.time() * 1000)
    note.resources = []
    png_resource = make_resource(png_path, "image/png")
    note.resources.append(png_resource)

    if os.path.exists(markdown_path):
        markdown_resource = make_resource(markdown_path, "text/plain")
        note.resources.append(markdown_resource)

    if os.path.exists(html_path):
        html_resource = make_resource(html_path, "text/html")
        note.resources.append(html_resource)

    note.title = title
    note.content = '<?xml version="1.0" encoding="UTF-8"?>'
    note.content += '<!DOCTYPE en-note SYSTEM ' \
        '"http://xml.evernote.com/pub/enml2.dtd">'
    note.content += '<en-note>'
    for resource in note.resources:
        note.content += '<en-media type="' + resource.mime + '" hash="' + binascii.hexlify(resource.data.bodyHash)+ '"/>'
    note.content += '</en-note>'
    return note_store.updateNote(auth_token, note)


def convert_to_png(i, o):
    t = tempfile.mktemp() + '.html'
    shutil.copyfile(i, t)
    subprocess.check_output(["webkit2png", "-x", "1024", "768", "-o", o, t])
    os.remove(t)


def convert_to_html(title, i, o):
    """把markdown 文件转换成html文件"""
    body = markdown2.markdown_path(i)
    with open(o, 'w') as f:
        f.write('''
                <html>
	            <head>
	                <meta charset="utf-8">
                    <title>{}</title>
	            </head>
                        <body>
                        {}
                        </body>
                </html>'''.format(title, body.encode('utf-8')))


def sync_evernotes(notebook, path):
    """同步当前目录的笔记到evernote notebook上"""
    _filter = NoteStore.NoteFilter()
    _filter.notebooksGuid = notebook.guid
    spec = NoteStore.NotesMetadataResultSpec()
    spec.includeTitle = True
    notelist = note_store.findNotesMetadata(_filter, 0,LimitsConstants.EDAM_USER_NOTES_MAX, spec)
    notes = {i.title:i for i in notelist.notes if i.deleted is None}

    local_notenames = set([i.split('.')[0] for i in os.listdir(path) if i.endswith('html') or i.endswith('md')])

    for local_notename in local_notenames:
        markdown_path = os.path.join(path, '{}.md'.format(local_notename))
        html_path = os.path.join(path, '{}.html'.format(local_notename))
        png_path = os.path.join(path, '{}.png'.format(local_notename))

        if os.path.exists(markdown_path):
            markdown_stat = os.stat(markdown_path)

            if os.path.exists(html_path):
                html_stat = os.stat(html_path)
                if markdown_stat.st_mtime > html_stat.st_mtime:
                    print("{} 更新时间大于 {}".format(markdown_path, html_path))
                    convert_to_html(local_notename, markdown_path, html_path)
            else:
                convert_to_html(local_notename, markdown_path, html_path)

        if os.path.exists(html_path):
            html_stat = os.stat(html_path)
            if os.path.exists(png_path):
                png_stat = os.stat(png_path)
                if html_stat.st_mtime > png_stat.st_mtime:
                    print("{} 更新时间大于 {}".format(html_path, png_path))
                    convert_to_png(html_path, png_path)
            else:
                convert_to_png(html_path, png_path)

        # png 一定存在

        if local_notename in notes:
            note = notes[local_notename]
            note = note_store.getNote(note.guid, True, True, True, True)
            png_stat = os.stat(png_path)
            if png_stat.st_mtime > note.updated/10**3:
                print("更新 {}".format(local_notename))
                markdown_path = os.path.join(path, '{}.md'.format(local_notename))
                if not os.path.exists(markdown_path):
                    markdown_path = None
                update_note(note, local_notename, png_path, markdown_path, html_path)
        else:
            print("创建 {}".format(local_notename))
            if not os.path.exists(markdown_path):
                markdown_path = None
            convert_to_png(html_path, png_path)
            create_note(local_notename, notebook, png_path, markdown_path, html_path)


def sync_to_evernotes(path):
    """将cmdmarkdown的文件更新到evernote中去"""
    evernotebooks = {i.name:i for i in note_store.listNotebooks()}
    for notebook_name in os.listdir(path):
        if notebook_name in evernotebooks:
            notebook = evernotebooks[notebook_name]
        else:
            notebook = Types.Notebook(name=notebook_name)
            note_store.createNotebook(notebook)
        sync_evernotes(notebook, os.path.join(path, notebook_name))


def main():
    sync_to_evernotes('./notes/')


if __name__ == '__main__':
    main()
