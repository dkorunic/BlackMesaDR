#!/bin/sh
# crude BlackMesa Disaster Recovery regression testing
# $Id: dry-run.sh,v 42565ddd2180 2010/10/23 16:34:47 dinko $

rsync -v --timeout=600 --dry-run --delete-after --password-file=/opt/BlackMesa-DR/password-file -a /dare/VMwareDataRecovery/. dare@10.4.224.41::dare/dare/VMwareDataRecovery/.
