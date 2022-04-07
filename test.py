# Из дельта переводим на обычный время опозданий
total_late_time = datetime.datetime.min + total_late_hours
if total_late_time.day == 1:
    hour = str(total_late_time.hour)
    minute = str(total_late_time.minute)
    if hour == '0':
        total_late = f"{minute} мин."
    else:
        total_late = f"{hour.lstrip('0')} час. {minute} мин."
else:
    day = int(total_late_time.strftime('%d')) - 1
    hour = str(total_late_time.hour)
    minute = str(total_late_time.minute)
    if hour == '0':
        total_late = f"{str(day)} дней {minute} мин."
    else:
        total_late = f"{str(day)} дней {hour.lstrip('0')} час. {minute} мин."

    total_late = total_late.lstrip('0')



# Из дельта переводим на обычный время раннего ухода
total_early_time = datetime.datetime.min + total_early_lived_time
if total_early_time.day == 1:
    hour = str(total_early_time.hour)
    minute = str(total_early_time.minute)
    if hour == '0':
        total_early = f"{minute} мин."
    else:
        total_early = f"{hour.lstrip('0')} час. {minute} мин."
else:
    day = int(total_early_time.strftime('%d')) - 1
    hour = str(total_early_time.hour)
    minute = str(total_early_time.minute)
    if hour == '0':
        total_early = f"{str(day)} дней {minute} мин."
    else:
        total_early = f"{str(day)} дней {hour.lstrip('0')} час. {minute} мин."

    total_early = total_early.lstrip('0')


    # Из дельта переводим на обычный время присутствия
    presence_time = datetime.datetime.min + total_presence_time
    if presence_time.day == 1:
        hour = str(presence_time.hour)
        minute = str(presence_time.minute)
        if hour == '0':
            total_presence = f"{minute} мин."
        else:
            total_presence = f"{hour.lstrip('0')} час. {minute} мин."
    else:
        day = int(presence_time.strftime('%d')) - 1
        hour = str(presence_time.hour)
        minute = str(presence_time.minute)
        if hour == '0':
            total_presence = f"{str(day)} дней {minute} мин."
        else:
            total_presence = f"{str(day)} дней {hour.lstrip('0')} час. {minute} мин."

        total_presence = total_presence.lstrip('0')
