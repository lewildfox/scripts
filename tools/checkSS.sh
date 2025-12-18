echo "==== InfraCNR - Softswitch DB-Backup & CDR creation ===="
echo "note: make sure backup & cdr are current..."

echo -e "\n\n#SS-BATAM:"
ssh softswitch@172.27.19.26 "hostname;date;echo '*latest DB-Backup*';ls -lrth /home/softswitch/dbbackup/ | tail -5 | awk '{print \$5,\$6,\$7,\$8,\$9}' | sed 's/_/-/g' ; echo '*Latest CDR*';ls -lrth /home/softswitch/CDR/ | tail -5 | awk '{print \$5,\$6,\$7,\$8,\$9}'"

echo -e "\n#SS-JAKARTA:"
ssh softswitch@172.27.19.18 "hostname;date;echo '*latest DB-Backup*';ls -lrth /home/softswitch/dbbackup/ | tail -5 | awk '{print \$5,\$6,\$7,\$8,\$9}' | sed 's/_/-/g'; echo '*Latest CDR*';ls -lrth /home/softswitch/data/ama/ | tail -5 | awk '{print \$5,\$6,\$7,\$8,\$9}'"

echo -e "\n#SS-SURABAYA:"
ssh softswitch@172.27.19.22 "hostname;date;echo '*latest DB-Backup*';ls -lrth /home/softswitch/dbbackup/ | grep -v 2136 | tail -5 | awk '{print \$5,\$6,\$7,\$8,\$9}' | sed 's/_/-/g';echo '*Latest CDR*';ls -lrth /home/softswitch/data/ama/ | tail -5 | awk '{print \$5,\$6,\$7,\$8,\$9}'"

echo -e "\n==== *SBC - LATEST MML BACKUP* ====="
echo -e "\n### HK ###"
ls -lrth /home/cdr/huawei_BACKUPMML/HK | tail -3 | awk '{print $5,$6,$7,$8,$9}'

echo -e "\n### SG ###"
ls -lrth /home/cdr/huawei_BACKUPMML/SG | tail -3 | awk '{print $5,$6,$7,$8,$9}'

echo -e "\n==== *VSO Server /home space* ====="
df -kh | grep vso-home | awk '{print $2,$3,$4,$5,$6}'
date