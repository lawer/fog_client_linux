# Copyright (C) 2013  Lars Wirzenius
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.


'''Simplistic text re-formatter.

This module format text, paragraph by paragraph, so it is somewhat
nice-looking, with no line too long, and short lines joined. In
other words, like what the textwrap library does. However, it
extends textwrap by recognising bulleted lists.

'''


import textwrap


class Paragraph(object):

    def __init__(self):
        self._lines = []

    def append(self, line):
        self._lines.append(line)

    def _oneliner(self):
        return ' '.join(' '.join(x.split()) for x in self._lines)

    def fill(self, width):
        filled = textwrap.fill(self._oneliner(), width=width)
        return filled


class BulletPoint(Paragraph):

    def fill(self, width):
        text = self._oneliner()
        assert text.startswith('* ')
        filled = textwrap.fill(text[2:], width=width - 2)
        lines = ['  %s' % x for x in filled.splitlines(True)]
        lines[0] = '* %s' % lines[0][2:]
        return ''.join(lines)


class EmptyLine(Paragraph):

    def fill(self, width):
        return ''


class TextFormat(object):

    def __init__(self, width=78):
        self._width = width

    def format(self, text):
        '''Return input string, but formatted nicely.'''

        filled_paras = []
        for para in self._paragraphs(text):
            filled_paras.append(para.fill(self._width))
        filled = '\n'.join(filled_paras)
        if text and not filled.endswith('\n'):
            filled += '\n'
        return filled

    def _paragraphs(self, text):

        def is_empty(line):
            return line.strip() == ''

        def is_bullet(line):
            return line.startswith('* ')

        def is_continuation(line):
            return line.startswith(' ')

        current = None
        in_list = False
        for line in text.splitlines(True):
            if in_list and is_continuation(line):
                assert current is not None
                current.append(line)
            elif is_bullet(line):
                if current:
                    yield current
                    if not in_list:
                        yield EmptyLine()
                current = BulletPoint()
                current.append(line)
                in_list = True
            elif is_empty(line):
                if current:
                    yield current
                    yield EmptyLine()
                current = None
                in_list = False
            else:
                if in_list:
                    yield current
                    yield EmptyLine()
                    current = None

                if not current:
                    current = Paragraph()
                current.append(line)
                in_list = False

        if current:
            yield current


