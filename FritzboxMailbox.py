#!/usr/bin/env python

# -*- coding: utf-8 -*-

from io import BytesIO
from datetime import datetime
from struct import Struct
from ftplib import FTP
from netrc import netrc


class Helper(object):

    @classmethod
    def nonull(cls, line):
        return str(line.split('\x00')[0])


class FormatException(Exception):
    def __init__(self, message, *args, **kwargs):
        self.message = message
        super(FormatException, self).__init__(message, *args, **kwargs)


class MailboxRecordingFile(object):

    __slots__ = ['filename', 'full_path', 'file_size']

    def __init__(self, filename=None, file_size=None, file_path=None):
        self.filename  = filename
        self.full_path  = file_path
        self.file_size  = file_size

    def __str__(self):
        return self.filename


class MailboxItem(object):

    __slots__ = ['data', 'encoding', 'raw_data']

    formatstring = '>Ib3x6I 20x 16s 56x 15s 17x 80s 48x 5B 31x 24sI' 

    def __init__(self, data):
        self.data       = data
        self.encoding   = 'latin-1'
        self.raw_data   = self.unpack(data)
        if self.ident != 348:
            raise FormatException('Unknown format identifier: %d' % self.ident)

    def __str__(self):
        return u'{time}\t{caller}\t{number}\t{duration}s\t{file}'.format(time=self.call_time, caller=self.caller_number,
        number=self.number, duration=self.duration, file=self.recording.filename)

    @classmethod
    def struct(cls):
        return  Struct(format=cls.formatstring)

    @classmethod
    def unpack(cls, data):
        return cls.struct().unpack_from(data)

    @classmethod
    def size(cls):
        return cls.struct().size

    @property
    def ident(self):
        return self.raw_data[0]

    @property
    def seq(self):
        return self.raw_data[1]

    @property
    def duration(self):
        return self.raw_data[5]

    @property
    def is_new(self):
        if self.raw_data[6] == 1:
            return True
        else:
            return False

    @property
    def sampling(self):
        return self.raw_data[3]

    @property
    def caller_number(self):
        return Helper.nonull(self.raw_data[8]).decode(self.encoding)

    @property
    def number(self):
        return Helper.nonull(self.raw_data[16]).decode(self.encoding)

    @property
    def call_time(self):
        (day, month, year, hour, minute) = self.raw_data[11:16]
        year += 2000
        return datetime(year, month, day, hour, minute)

    @property
    def recording(self):
        mrf = MailboxRecordingFile()
        mrf.filename  = Helper.nonull(self.raw_data[9]).decode(self.encoding)
        mrf.full_path  = Helper.nonull(self.raw_data[10]).decode(self.encoding)
        mrf.file_size  = self.raw_data[4]
        return mrf

    def dump(self):
        return self.raw_data
        

class MailboxReader(object):
    """
     Grobe Info http://www.ip-symcon.de/forum/threads/11555-Fritzbox-Anrufbeantworter?highlight=meta0
    """

    __slots__ = ['mailbox_file']

    def __init__(self, mailbox_file=None):
        self.mailbox_file   = mailbox_file 

    def __enter__(self):
        return self.__iter__()

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type:
            return False

    def __iter__(self):
        with self.mailbox_file as f:
            while True:
                data = f.read(MailboxItem.size())
                if not data: break
                yield MailboxItem(data)


class FtpReaderException(Exception):
    def __init__(self, message, *args, **kwargs):
        self.message = message
        super(FtpReaderException, self).__init__(message, *args, **kwargs)

class FtpReader(BytesIO):
    """
        Almost no Error handling

        buffer = FtpReader(host='fritz.home.kerpe.net')
        buffer.connect()
        with buffer as f:
            buffer.read(123)
    """
    __slots__ = ['host', 'user', 'password', 'basepath', 'filename', 'data']

    def __init__(self, host='fritz.box', user='', password='', use_netrc=True, basepath='voicebox'):
        self.host       = host
        self.use_netrc  = use_netrc
        self.user       = user
        self.password   = password
        self.basepath   = basepath
        self.filename   = None
        self.data       = None
        self._netrc_credentials()
        super(FtpReader, self).__init__()

    def _netrc_credentials(self):
        if self.use_netrc:
            nrc = netrc()
            (user, account, password)  = nrc.authenticators(self.host)
            if user:
                self.user = user
            if password:
                self.password = password
    
    def connect(self):
        try:
            self._conn = FTP(self.host)
        except (Exception, e):
            raise FtpReaderException('could not connect to host: ' + str(e))
        self._conn.login(self.user, self.password)
        if self.basepath:
            self._conn.cwd(self.basepath)
       
    def read_file(self, filename='meta0', path=None):
        if not self._conn:
            raise FtpReaderException('Not connected')
        self.filename = filename
        if path:
            self._conn.cwd(path)
        self._conn.retrbinary ('RETR '+ self.filename , self.write)
        self.flush()
        self.seek(0)

    def close(self):
        self._conn.quit()


if __name__ == '__main__':

    fbftp = FtpReader(host='192.168.178.1', use_netrc=True)
    fbftp.connect()
    fbftp.read_file('meta0')
    
    mbf = fbftp
    #mbf = io.open('meta0', 'rb')

    mb = MailboxReader(mbf)

    with MailboxReader(mbf) as mb:
        for record in mb:
            if record.is_new:
                flag = '* '
            else:
                flag = '- '
            print(flag + str(record))
            print(record.dump())


