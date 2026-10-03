import struct
import re


def compile_po(po_path, mo_path):
    messages = {}
    with open(po_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_msgid = None
    for line in lines:
        line = line.strip()
        if line.startswith('msgid '):
            current_msgid = line[7:-1]
        elif line.startswith('msgstr ') and current_msgid is not None:
            msgstr = line[8:-1]
            if current_msgid:
                messages[
                    current_msgid.encode('utf-8')] = msgstr.encode('utf-8')
            current_msgid = None

    keys = sorted(messages.keys())
    offsets = []
    ids = b''
    strs = b''

    for k in keys:
        offsets.append((len(ids), len(k), len(strs), len(messages[k])))
        ids += k + b'\x00'
        strs += messages[k] + b'\x00'

    keystart = 28 + 16 * len(keys)
    valstart = keystart + len(ids)

    keyoffsets = []
    valoffsets = []
    for o1, l1, o2, l2 in offsets:
        keyoffsets.append((l1, keystart + o1))
        valoffsets.append((l2, valstart + o2))

    output = struct.pack('IIIIIII',
        0x950412de,  # Magic
        0,          # Version
        len(keys),  # Count
        28,         # Offset to key index
        28 + 8 * len(keys),  # Offset to value index
        0, 0        # Hash table
    )

    for l, o in keyoffsets:
        output += struct.pack('II', l, o)
    for l, o in valoffsets:
        output += struct.pack('II', l, o)

    output += ids + strs
    with open(mo_path, 'wb') as f:
        f.write(output)
    print('Successfully generated django.mo binary translation file!')

if __name__ == '__main__':
    compile_po('locale/sw/LC_MESSAGES/django.po', 'locale/sw/LC_MESSAGES/django.mo')
