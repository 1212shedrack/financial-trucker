"""
Compile django.po to django.mo without needing GNU gettext tools.
Uses Python's built-in msgfmt module.
"""
import sys
import os

# Change to project root
os.chdir(os.path.dirname(os.path.abspath(__file__)))

po_path = os.path.join('locale', 'sw', 'LC_MESSAGES', 'django.po')
mo_path = os.path.join('locale', 'sw', 'LC_MESSAGES', 'django.mo')

# Simple .po to .mo compiler using Python struct
import struct
import array

def compile_po(po_file, mo_file):
    """Minimal but correct PO->MO compiler."""
    messages = {}
    msgid = None
    msgstr = None
    in_msgid = False
    in_msgstr = False

    def unescape(s):
        s = s[1:-1]  # strip quotes
        s = s.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace('\\\\', '\\')
        return s

    with open(po_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.rstrip('\n')
        if line.startswith('#') or line.strip() == '':
            if msgid is not None and msgstr is not None and msgid != '':
                messages[msgid] = msgstr
            if line.strip() == '':
                msgid = None
                msgstr = None
                in_msgid = False
                in_msgstr = False
            continue
        if line.startswith('msgid '):
            if msgid is not None and msgstr is not None and msgid != '':
                messages[msgid] = msgstr
            msgid = unescape(line[6:].strip())
            msgstr = None
            in_msgid = True
            in_msgstr = False
        elif line.startswith('msgstr '):
            msgstr = unescape(line[7:].strip())
            in_msgid = False
            in_msgstr = True
        elif line.startswith('"') and in_msgid:
            msgid += unescape(line.strip())
        elif line.startswith('"') and in_msgstr:
            msgstr += unescape(line.strip())

    if msgid is not None and msgstr is not None and msgid != '':
        messages[msgid] = msgstr

    # Build .mo binary
    keys = sorted(messages.keys())
    offsets = []
    ids = b''
    strs = b''

    for k in keys:
        v = messages[k]
        kb = k.encode('utf-8')
        vb = v.encode('utf-8')
        offsets.append((len(ids), len(kb), len(strs), len(vb)))
        ids += kb + b'\x00'
        strs += vb + b'\x00'

    n = len(keys)
    keystart = 7 * 4 + 16 * n
    valuestart = keystart + len(ids)

    koffsets = []
    voffsets = []
    for o in offsets:
        koffsets += [o[1], keystart + o[0]]
        voffsets += [o[3], valuestart + o[2]]

    output = struct.pack('Iiiiiii',
        0x950412de,  # magic
        0,           # revision
        n,
        7 * 4,       # offset of key table
        7 * 4 + n * 8,  # offset of value table
        0, 0)        # hash table (unused)

    output += struct.pack('ii' * n, *koffsets)
    output += struct.pack('ii' * n, *voffsets)
    output += ids
    output += strs

    with open(mo_file, 'wb') as f:
        f.write(output)

    print(f"Compiled {n} messages from {po_file} -> {mo_file}")

compile_po(po_path, mo_path)
