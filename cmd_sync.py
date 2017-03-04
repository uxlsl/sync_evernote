# -*- coding:utf-8 -*-
import os
import tempfile
import shutil
import subprocess
import binascii
import hashlib
import evernote.edam.userstore.constants as UserStoreConstants
from evernote.edam.limits import constants as LimitsConstants
import evernote.edam.type.ttypes as Types
from evernote.edam.notestore import NoteStore

from evernote.api.client import EvernoteClient

# https://sandbox.evernote.com/api/DeveloperToken.action
auth_token = "S=s1:U=936b9:E=161eec32d39:C=15a9711fd58:P=1cd:A=en-devtoken:V=2:H=84efd847b77ab952fc720c4db9264ef9"

if auth_token == "your developer token":
    print "Please fill in your developer token"
    print "To get a developer token, visit " \
        "https://sandbox.evernote.com/api/DeveloperToken.action"
    exit(1)

client = EvernoteClient(token=auth_token, sandbox=True)

user_store = client.get_user_store()

version_ok = user_store.checkVersion(
    "Evernote EDAMTest (Python)",
    UserStoreConstants.EDAM_VERSION_MAJOR,
    UserStoreConstants.EDAM_VERSION_MINOR
)
print "Is my Evernote API version up to date? ", str(version_ok)
print ""
if not version_ok:
    exit(1)

note_store = client.get_note_store()


def create_png_note(title, png_path,notebook):
    """
    `title`: 标题
    `filename`: 文件名
    """
    note = Types.Note()
    note.notebookGuid = notebook.guid
    image = open(png_path, 'rb').read()
    md5 = hashlib.md5()
    md5.update(image)
    hash = md5.digest()
    data = Types.Data()
    data.size = len(image)
    data.bodyHash = hash
    data.body = image
    resource = Types.Resource()
    resource.mime = 'image/png'
    resource.data = data
    note.resources = [resource]
    hash_hex = binascii.hexlify(hash)
    note.title = title
    note.content = '<?xml version="1.0" encoding="UTF-8"?>'
    note.content += '<!DOCTYPE en-note SYSTEM ' \
        '"http://xml.evernote.com/pub/enml2.dtd">'
    note.content += '<en-note>'
    note.content += '<en-media type="image/png" hash="' + hash_hex + '"/>'
    note.content += '</en-note>'
    return note_store.createNote(note)


def update_png_note(note, title, png_path):
    """
    `title`: 标题
    `filename`: 文件名
    """
    image = open(png_path, 'rb').read()
    md5 = hashlib.md5()
    md5.update(image)
    hash = md5.digest()
    data = Types.Data()
    data.size = len(image)
    data.bodyHash = hash
    data.body = image
    resource = Types.Resource()
    resource.mime = 'image/png'
    resource.data = data
    note.resources = [resource]
    hash_hex = binascii.hexlify(hash)
    note.title = title
    note.content = '<?xml version="1.0" encoding="UTF-8"?>'
    note.content += '<!DOCTYPE en-note SYSTEM ' \
        '"http://xml.evernote.com/pub/enml2.dtd">'
    note.content += '<en-note>'
    note.content += '<en-media type="image/png" hash="' + hash_hex + '"/>'
    note.content += '</en-note>'
    return note_store.updateNote(note)


def convert_to_png(i, o):
    t = tempfile.mktemp() + '.html'
    shutil.copyfile(i, t)
    subprocess.check_output(["webkit2png", "-o", o, t])
    os.remove(t)


def sync_evernotes(notebook, path):
    """同步当前目录的笔记到evernote notebook上"""
    _filter = NoteStore.NoteFilter()
    _filter.notebooksGuid = notebook.guid
    spec = NoteStore.NotesMetadataResultSpec()
    spec.includeTitle = True
    notelist = note_store.findNotesMetadata(_filter, 0,LimitsConstants.EDAM_USER_NOTES_MAX, spec)
    notes = {i.title:i for i in notelist.notes}

    for filename in os.listdir(path):
        notename, fmt = filename.split('.')
        if fmt != 'html':
            continue
        if notename in notes:
            note = notes[notename]
            file_stat = os.stat(os.path.join(path, filename))
            if file_stat.st_mtime > note.updated:
                print("更新 {}".format(notename))
                png_path = os.path.join(path, '{}.png'.format(notename))
                convert_to_png(os.path.join(path, filename), png_path)
                update_png_note(note, notename, png_path)
        else:
            print("创建 {}".format(notename))
            png_path = os.path.join(path, '{}.png'.format(notename))
            convert_to_png(os.path.join(path, filename), png_path)
            create_png_note(notename, png_path, notebook)


def cmd_to_evernotes(path):
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
    cmd_to_evernotes('./cmdnotes/')


if __name__ == '__main__':
    main()
