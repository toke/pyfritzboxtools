pyfritzboxtools
===============

My personal python FritzBox helpers

Currently a basic fetching and parsing of Mailbox message
status via ftp is implemented.


```
from FritzboxMailbox import MailboxReader, FtpReader

fbftp = FtpReader(host='fritz.box', use_netrc=True)
fbftp.connect()


mbf = fbftp
# Alternative use local file
#mbf = io.open('meta0', 'rb')

mb = MailboxReader(mbf)

with MailboxReader(mbf) as mb:
    for record in mb:
        if record.is_new:
            flag = '* '
        else:
            flag = '- '
        print(flag + str(record))
```

