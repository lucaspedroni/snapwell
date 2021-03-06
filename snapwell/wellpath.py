#  Copyright (C) 2016  Statoil ASA, Norway.
#
#  This file is part of Snapwell.
#
#  Snapwell is free software: you can redistribute it and/or modify it under the
#  terms of the GNU General Public License as published by the Free Software
#  Foundation, either version 3 of the License, or (at your option) any later
#  version.
#
#  Snapwell is distributed in the hope that it will be useful, but WITHOUT ANY
#  WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
#  A PARTICULAR PURPOSE.
#
#  See the GNU General Public License at <http://www.gnu.org/licenses/gpl.html>
#  for more details.

from snap_utils import read_next_tokenline as token
from snap_utils import Nan, Inf
from snap_utils import finiteFloat, tryFloat, close

class WellPath:
    """A WellPath is essentially a dictionary of lists containing at the very least,
       x (UTM), y (UTM), z (UTM, TVD), followed by an arbitrary amount of well
       logs (specified in WellPath file), e.g. measured depth, inclination, and
       azimuth.

       (This is essentially a very basic Excel file, with some minimal metadata.)

       Can also contain z-opt, z-diff, permx, swat values etc.

    """

    def __init__(self, version=1.0, welltype='', wellname='', filename=None):
        self._table    = {'x':[],'y':[],'z':[]}
        self._version  = version
        self._welltype = welltype
        self._wellname = wellname
        self._headers  = ['x','y','z']
        self._filename = filename
        self._rkb = (0.0, 0.0, 0.0)
        self._depthtype = None
        self._windowdepth = -Inf
        if filename and len(filename) > 3 and filename[-3:] == '.sc':
            print('Warning:  WellPath file extension is .sc.  Potentially a Snapwell config file.')

    def filename(self):
        return self._filename

    def setFilename(self, fname):
        self._filename = fname

    def setRkb(self, rkb):
        """Set RKB (x,y,z) to be given triple.  Need a triple of float-able values."""
        if len(rkb) != 3:
            raise IndexError('Need a triple (x,y,z) of floats, not %s' % str(rkb))
        try:
            t = float(rkb[0]), float(rkb[1]), float(rkb[2])
            self._rkb = t
        except ValueError:
            raise ValueError('Need x,y,z to be floats, got (%s, %s, %s)'
                             % (str(type(rkb[0])), str(type(rkb[1])), str(type(rkb[2]))))

    def rkb(self):
        x,y,z = self._rkb[0],self._rkb[1],self._rkb[2]
        return (float(x), float(y), float(z))

    def depthType(self):
        return self._depthtype
    def windowDepth(self):
        return self._windowdepth

    def setDepthType(self, depthtype):
        """If None, resets windowdepth to -inf, else must be MD or TVD."""
        if not depthtype:
            self._windowdepth = -Inf
            self._depthtype = None
        elif depthtype in ['MD', 'TVD']:
            self._depthtype = depthtype
        else:
            raise ValueError('Window depth type must be None, "MD", or "TVD", not %s' % depthtype)

    def setWindowDepth(self, depth):
        self._windowdepth = float(depth)

    def addColumn(self, header, data=None):
        if not data:
            data = []
        if header in self._table:
            raise KeyError('Key %s exists in table.' % header)
        lx = len(self)
        ld = len(data)
        if ld != lx:
            raise IndexError('Data needs to be of len(wp)=%d, was given %d entries.'
                             % (lx,ld))
        self._table[header] = data
        self._headers.append(header)

    def removeColumn(self, header):
        if header in ['x','y','z']:
            raise ValueError('Cannot delete column %s.  A WellPath must contain x, y, and z.'
                             % str(header))
        if header in self._table:
            del self._table[header]
            hs = [h for h in self._headers if h != header]
            self._headers = hs

    def addRow(self, row):
        insert = {}
        # doing it like this makes us never need to rollback
        for key in self._table:
            insert[key] = row[key] # consider catch/re-raise w/better msg
        for key in insert:
            self._table[key].append(insert[key])

    def addRaw(self, row):
        """Adds a raw row, where row now is a list following header's order"""
        if len(row) != len(self._table):
            raise IndexError('Cannot insert %s into table of %d columns.' %
                             (row, len(self._table)))
        idx = 0
        for key in self._headers:
            self._table[key].append(row[idx])
            idx += 1

        if len(self) == 1:
            self.updateRkb()


    def headers(self):
        return self._headers

    def rows(self):
        for i in range(len(self)):
            yield [self._table[c][i] for c in self._headers]

    def version(self):
        return self._version

    def setVersion(self, version):
        self._version = version


    def welltype(self):
        return self._welltype

    def setWelltype(self, welltype):
        self._welltype = welltype


    def wellname(self):
        return self._wellname

    def setWellname(self, wellname):
        self._wellname = wellname

    def updateRkb(self):
        """Updates the RKB values to the correct ones, that is, rkb=(x, y, z_r) where x
           and y are the x and y values of the first path point and the z_r is
           MD-TVD for the first point.

           In the case where MD or TVD are not finite floats for the first
           point, this function will do nothing and return False.  The function
           returns true if all conditions for value updating is met.

        """
        if len(self) == 0:
            return False
        if 'MD' not in self._headers:
            return False
        x,y    = self._table['x'][0], self._table['y'][0]
        tvd,md = self._table['z'][0], self._table['MD'][0]
        if finiteFloat(md) and finiteFloat(tvd):
            self.setRkb((x,y,md-tvd))
            return True
        else:
            return False

    def update(self, col, idx, elt):

        """Sets elt in the idx'th position of column col."""
        rs = len(self)
        cs = len(self._headers)
        if not 0 <= idx < rs:
            raise IndexError('row index out of range, 0 <= idx < %d'    % rs)

        if isinstance( col, (int,long) ):
            if not 0 <= col < cs:
                raise IndexError('column index out of range, 0 <= col < %d' % cs)
            col = self._headers[col]

        if not col in self._headers:
            raise KeyError('Key %s does not name a column' % str(col))

        self._table[col][idx] = elt

    def __iter__(self):
        return self

    def __getitem__(self, idx):
        if type(idx) == type(''):
            return self._table[idx]
        return [self._table[key][idx] for key in self._headers]

    def __setitem__(self, idx, elt):
        if type(elt) == type({}):
            for key in self._table:
                insert[key] = elt[key]
            for key in insert:
                self._table[key][idx] = insert[key]
        else:
            lx = len(self._headers)
            ld = len(elt)
            for i in range(min(lx,ld)):
                h = self._headers[i]
                self._table[h][idx] = elt[i]
        if idx == 0:
            self.updateRkb()

    def __len__(self):
        """The number of rows, i.e., the number of wellpoints.
        """
        return len(self._table['x'])

    def __str__(self):
        return self._wellname

    @staticmethod
    def parse(fname):
        """Given a filename, parses and returns a WellPath object.
               * easting  (X UTM)
               * northing (Y UTM)
               * tvd mls  (Z UTM, true vertical depth)
               * ...      (specified in format file, see readme)
        """

        f = open(fname, "r")

        version =   token(f)
        well_type = token(f)

        # well_name and RKB
        wellconfig = token(f).split()
        well_name = wellconfig[0]
        rkb_x, rkb_y, rkb_z = 0,0,0
        if len(wellconfig) > 1:
            rkb_x = tryFloat(wellconfig[1])
        if len(wellconfig) > 2:
            rkb_y = tryFloat(wellconfig[2])
        if len(wellconfig) > 3:
            rkb_z = tryFloat(wellconfig[3])

        wp = WellPath(version = version, welltype=well_type, wellname=well_name, filename=fname)
        wp.setRkb((rkb_x, rkb_y, rkb_z))

        num_columns = 0
        num_columns_line = token(f)
        try:
            num_columns = int(num_columns_line)
        except ValueError as err:
            print('Could not parse required <num_logs> integer, is this really a WellPath file?')
            raise ValueError('Could not parse WellPath file %s: %s' % (fname, err))

        for i in range(num_columns):
            header = token(f).split()[0] # ignore unit,scale for now
            wp.addColumn(header)

        while True: # loop-and-a-half
            t = token(f)
            if t is None:
                break
            data = map(float, t.split())
            wp.addRaw(data)
        f.close()

        return wp

    def write(self, fname=None, overwrite=False, resinsight=False):
        """Opens fname and writes this object to file in the typical WellPath format
           (see readme).  If fname exists and overwrite is not explicitly set to
           True, this method will throw.

           The output is version\ntype\nname\n0\ndata where data is len(this)
           many lines of three (space separated) columns with the columns being,
           respectively, x (utm), y (utm) and z (utm), the latter being the new
           depth-optimized output.

        """
        if not fname:
            if not self._filename:
                raise ValueError('WellPath.filename is unspecified and fname not provided.  '
                                 'Need at least one.')
            else:
                fname = '%s.out' % self._filename
        if not overwrite:
            from os.path import exists
            if exists(fname):
                raise IOError("Filename %s exists, cannot overwrite unless explicitly told to!"
                              % fname)


        fmt = lambda s: '%.2f' % s
        out_rkb = " ".join(map(fmt, self._rkb))
        nl = '\n'
        head = '%s%s%s%s%s %s%s%s%s' % (
            str(self._version), nl,
            str(self._welltype), nl,
            str(self._wellname), out_rkb, nl,
            str(len(self._headers) - 3), nl)

        if resinsight:
            head = str(self._wellname)

        logs = ''
        linecount = 0 # number of rows output
        for i in range(3, len(self._headers)):
            logs += '%s %s %s%s' % (self._headers[i], "1", "lin", nl) # support lin

        if resinsight:
            logs = nl

        body = ''
        for r in self.rows():
            if not resinsight:
                body += " ".join(map(fmt, r)) + nl
            else:
                body += " ".join(map(fmt, r[:4])) + nl # ResInsight wants only 'x y tvd md'
            linecount += 1

        # Writing file ...
        with open(fname, "w") as out:
            out.write(head+logs+body)

        return linecount


    def __eq__(self, other):
        try:
            len_s,len_o = len(self), len(other)
            wid_s,wid_o = len(self._headers), len(other._headers)
            if len_s != len_o:
                return False
            if wid_s != wid_o:
                return False
            for h in self._headers:
                if not h in other._headers:
                    return False
                col_s = self._table[h]
                col_o = other._table[h]
                for i in range(len_s):
                    if not close(col_s[i], col_o[i]):
                        print('Object differ in col %s, row %d: %f vs %f'
                              % (h,i,col_s[i], col_o[i]))
                        return False
            return True
        except AttributeError:
            return False


    def __ne__(self,other):
        return not (self == other)
