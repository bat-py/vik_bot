import datetime

for i in range(10):
    try:
        a = i/0
    except Exception as e:
        with open('journal.txt', 'a') as w:
            w.write(datetime.datetime.now().strftime('%d.%m.%Y %H:%M  ') + \
                    'checkup.check_users_in_logs(admins_list):\n' + str(e) + '\n\n')
