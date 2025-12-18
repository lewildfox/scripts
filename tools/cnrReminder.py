import sys
import telegram

teletoken = '1246959217:AAGXaQacKWpOy-9FnxtcWb0sbRQrgm3LWnw'
chatid = '-417009902'
logg = open("/home/eburwic/reminders_cnr/cekss.out", "r")
logg2 = open("/home/eburwic/reminders_cnr/cekss.out", "rb")

def sendtele(msg, chat_id, token):
	bot = telegram.Bot(token=token)
	bot.sendMessage(text=msg, chat_id=chat_id, parse_mode='markdown')
	bot.sendDocument(chat_id=chat_id, document=logg2)

pesan = "\xE2\x9D\x97 *[REMINDER]* Please fill out InfraCNR checklist at http://cnr.telin.co.id/infracnr/sernode/checklist/pelaksanaan" + '\n\n' + "Data Sources:" + '\n' + "http://vso.telin.co.id/books/healthy-check/page/cnr-checklist-data-sources"

#logg = open("/home/eburwic/reminders_cnr/cekss.out", "r")
#print(pesan + '\n\n' + logg.read())

sendtele(msg=pesan + '\n\n' + logg.read(), chat_id=chatid, token=teletoken)

logg.close()
logg2.close()