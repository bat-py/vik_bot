import datetime
import configparser
import sql_handler
import xlsxwriter
import collections
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

config = configparser.ConfigParser()
config.read('config.ini')


class WorkerReport:
    """
    Создает полный отчет для одного человека за выбранный период
    """

    def __init__(self, worker_id, chosen_days, chosen_days_str):
        # self.term = term
        self.worker_id = worker_id

        # Составим список дней с объектами date() указанного периода для цикла: [..., datetime.datetime.now().date()]
        self.chosen_days = chosen_days
        self.chosen_days_str = chosen_days_str
        # in_history или out_history может хранит библиотеку где ключ это день(date элемент): {date : in_time, ..}
        self.in_history, self.out_history, self.in_history_str, self.out_history_str = self.get_in_out_history()

        # Получает dict объект с записями тех дней который опоздал: {date: time_of_late}.
        self.late_history = self.get_late_history()

        # Получает dict объект с записями тех дней который ушел раньше: {date: early_leaved_time}.
        self.early_leaved_history = self.get_early_leaved_history()

        # Получает dict объект с записями тех дней который не пришел: {date: True}.
        self.missed_days_history = self.get_missed_days_history()

        # comments может хранить комментарий или если сотрудник не оставил его тогда 'empty': {date: commnet, ..} или {date: 'empty', ..}
        # locations может хранить геолокацию или если сотрудник не оставил его тогда 'empty': {date: location, ..} или {date: 'empty', ..}
        self.comments, self.locations = self.get_comment_and_locations()

    def get_in_out_history(self):
        # Хранит библиотеку где ключ это день(date элемент): { date : in_time, ...}
        # Каждый объект может хранит: {in: time} или {in: False}
        in_history = {}
        # Тут будет тоже самое что и в in_history, но вместо объекта time будет хранить в str формате
        in_history_str = {}
        # Хранит библиотеку где ключ это день(date элемент): { date : out: out_time, ...}
        out_history = {}
        out_history_str = {}

        for day in self.chosen_days:
            # Может возвращать 3 варианта:
            #     Когда нету входа: False
            #     Когда есть входа в выхода нет: (in_time, False)
            #     Когда есть вход и выход: (in_time, out_time)
            in_out_time = sql_handler.get_user_in_out_history(self.worker_id, day)

            if in_out_time:
                in_history[day] = in_out_time[0]
                in_history_str[day] = in_out_time[0].strftime('%H:%M')
                # Если есть время ухода:
                if in_out_time[1]:
                    out_history[day] = in_out_time[1]
                    out_history_str[day] = in_out_time[1].strftime('%H:%M')
                else:
                    out_history[day] = '-'
                    out_history_str[day] = '-'
            else:
                in_history[day] = '-'
                in_history_str[day] = '-'
                out_history[day] = '-'
                out_history_str[day] = '-'

        return in_history, out_history, in_history_str, out_history_str

    def get_late_history(self):
        """
        :return: Те дни который сотрудник опоздал: {date: late_time} или если не
        """
        late_history = {}

        start_time_delta = datetime.timedelta(
            hours=int(config['time']['start_hour']),
            minutes=int(config['time']['start_minute'])
        )

        ten_min_delta = datetime.timedelta(minutes=10)

        for date, in_time in self.in_history.items():
            if in_time == '-':
                # Добавим в библиотеку late_history: {date: 0} если в указанный день не пришел
                late_history[date] = 0
            # Если in_time не '-'
            else:
                in_time_delta = datetime.timedelta(
                    hours=in_time.hour,
                    minutes=in_time.minute,
                    seconds=in_time.second
                )

                # Если пришел после 9:10, тогда добавим этот день как опоздавший
                if in_time_delta > start_time_delta + ten_min_delta:
                    # Определим на сколько он опоздал
                    late_time = datetime.datetime.min + (in_time_delta - start_time_delta)

                    # Добавим в библиотеку late_history: {date: late_time}
                    late_history[date] = late_time.strftime('%H:%M')
                else:
                    # Добавим в библиотеку late_history: {date: 0} если в указанный день пришел во время
                    late_history[date] = 0

        return late_history

    def get_early_leaved_history(self):
        """
        :return: Те дни который сотрудник ушел раньше времени: {date: late_time} или если ешел во время, тогда {date: False}
        """
        early_leaved_history = {}

        end_time_delta = datetime.timedelta(
            hours=int(config['time']['end_hour']),
            minutes=int(config['time']['end_minute'])
        )

        for date, out_time in self.out_history.items():
            # Если не пришел в указаныый день, тогда будет просто 0
            if out_time == '-':
                early_leaved_history[date] = 0
            else:
                out_time_delta = datetime.timedelta(
                    hours=out_time.hour,
                    minutes=out_time.minute,
                    seconds=out_time.second
                )

                # Если ушел раньше времени
                if out_time_delta < end_time_delta:
                    # Определим на сколько он ушел раньше времени
                    early_leaved_time = datetime.datetime.min + (end_time_delta - out_time_delta)

                    # Так как мы секунды сбрасываем, чтобы всё выглядело правильно мы должны вместо 5:10:15 должны показать 5:11
                    # Но если сукунд == 0, значит вместо 5:10:0 покажем 5:10
                    if early_leaved_time.second != 0:
                        early_leaved_time += datetime.timedelta(minutes=1)

                    # Добавим в библиотеку early_leaved_history: {date: late_time}
                    early_leaved_history[date] = early_leaved_time.strftime('%H:%M')

                # Если ушел после окончания дня, тогда просто будет 0
                else:
                    early_leaved_history[date] = 0

        return early_leaved_history

    def get_missed_days_history(self):
        missed_days = {}

        for date, in_time in self.in_history.items():
            if in_time == '-':
                missed_days[date] = '+'
            else:
                missed_days[date] = 0

        return missed_days

    def get_comment_and_locations(self):
        # Может хранить комментарий или если сотрудник не оставил его тогда 'empty': {date: commnet, ..} или {date: 'empty', ..}
        comments = {}
        # Может хранить геолокацию или если сотрудник не оставил его тогда 'empty': {date: location, ..} или {date: 'empty', ..}
        locations = {}

        # Получаем из таблицы "report" все информации об опоздании по id этого человека за выбранный срок:
        # [(id, user_id, date, comment, time, location), ...], где каждый элемент это отдельный день
        worker_report_list = sql_handler.get_report_by_term_for_excel(self.worker_id, self.chosen_days[0],
                                                                      self.chosen_days[-1])
        # Из worker_report_list создадим библиотеку: {date: (id, user_id, date, comment, time), ...}
        worker_report_dict = {}
        for day in worker_report_list:
            worker_report_dict[day[2]] = day

        for date in self.chosen_days:
            report = worker_report_dict.get(date)

            # Если нашелся такой день в worker_report_dict
            if report:
                # Может этот день нашелся в worker_report_dict, но возможно сотрудник не оставил комментарий или геолок.
                if report[3]:
                    comments[date] = report[3]
                else:
                    comments[date] = '-'

                if report[5]:
                    location_latitude_longitude = ','.join(report[5])
                    latitude = location_latitude_longitude[0]
                    longitude = location_latitude_longitude[1]
                    location_url = f"https://www.google.com/maps?q={latitude},{longitude}&ll={latitude},{longitude}&z=16"

                    locations[date] = location_url
                else:
                    locations[date] = '-'
            else:
                comments[date] = '-'
                locations[date] = '-'

        return comments, locations


def excel_report_creator_first_type(term):
    # Define term and file name
    # Если term == month значит scheduler запустил эту функцию в 0:00. В таком случае определим term и имя файла будет "report.xlsx"
    if term == 'month':
        # Excel file name
        dic_name = 'excel_files'
        file_name = 'report1.xlsx'
        file_path = dic_name + '/' + file_name

        # Последний день отчета. В таком случае это день назад
        report_end_day = datetime.datetime.now().date() - datetime.timedelta(days=1)
        day = report_end_day.day
        check_days = report_end_day

        chosen_days = []
        chosen_days_str = []

        # Например цикл начался с 19.04.2022, значит цикл будет продолжатся до 19.03.2022
        while True:
            chosen_days.append(check_days)
            chosen_days_str.append(check_days.strftime('%d.%m.%Y'))

            check_days -= datetime.timedelta(days=1)

            # Если цикл начался с 19.04.2022, значит цикл остановиться в 19.03.2022
            if check_days.day == day:
                break

        chosen_days.sort()
        chosen_days_str.sort()

    # Если админ хочет не месяца несколько дней (который сам же указал: От 1-30 дней)
    else:
        pass

    # Create a workbook and add a worksheet.
    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet()

    # Создаем форматы для ячеек загаловок
    title_format = workbook.add_format({'bold': True, 'bg_color': '#82d513'})
    fio_format = workbook.add_format({'bold': True, 'bg_color': '#73a0d0'})
    # Формат для сталбцов: "Дата\n Приход\n Уход\n Опоздание\n Ранний уход..."
    data_field_format = workbook.add_format({'bold': True, 'bg_color': '#c0829f'})

    worksheet.set_column(0, 0, 18)
    worksheet.set_column(1, 1, 12)
    worksheet.set_column(2, 6, 9)
    worksheet.set_column(7, 8, 18)

    row = 2
    column = 0

    # Создаем титульную часть excel файла. Сперва добавим отступ чтобы текст был в середине экрана
    title = ' ' * 70 + config['excel']['title']

    # Запишем титульную часть документа
    worksheet.merge_range(row, 0, row, 8, title, title_format)
    # Перейдем на следующую строку
    row += 1

    # Создаем msg типа: "С: 2022-04-01 до: 2022-04-30"
    end_date = chosen_days_str[-1]
    start_date = chosen_days_str[0]
    date_str = f"{' ' * 80}С: {start_date} до: {end_date}"

    # Запишем промежуток: "С: 2022-04-01 до: 2022-04-30"
    worksheet.merge_range(row, 0, row, 8, date_str, title_format)
    # Перейдем на следующую строку
    row += 2

    columns = [
        config['excel']['worker_name'],
        config['excel']['date'],
        config['excel']['came'],
        config['excel']['leave'],
        config['excel']['late'],
        config['excel']['early_leave'],
        config['excel']['missed_days'],
        config['excel']['comments'],
        config['excel']['locations'],
    ]

    worksheet.write_row(row, 0, columns, data_field_format)
    row += 1
    # Получаем список всех рабочих(who=control): [(ID, name, Who, chat_id), ...]
    all_workers = sql_handler.get_all_workers()

    # В excel отчете у каждого будет свой отдельный блок.
    for worker in [[31, 'rixsimov']]:
    #for worker in all_workers:
        # Получаем все данные сотрудника за выбранный срок
        worker_report = WorkerReport(worker[0], chosen_days, chosen_days_str)

        for day in worker_report.in_history.keys():
            row_data = [
                worker[1],
                day.strftime('%d.%m.%Y'),
                worker_report.in_history_str[day],
                worker_report.out_history_str[day],
                worker_report.late_history[day],
                worker_report.early_leaved_history[day],
                worker_report.missed_days_history[day],
                worker_report.comments[day],
                worker_report.locations[day]
            ]

            worksheet.write_row(row, 0, row_data)

            row += 1

        # Между каждый сотрудником будет одна пустая строка в excel файле
        row += 1

    # Сохнарим созданный excel файл
    workbook.close()


def excel_report_creator_second_type(term):
    # Define term and file name
    # Если term == month значит scheduler запустил эту функцию в 0:00. В таком случае определим term и имя файла будет "report.xlsx"
    if term == 'month':
        # Excel file name
        dic_name = 'excel_files'
        file_name = 'report2.xlsx'
        file_path = dic_name + '/' + file_name

        # Последний день отчета. В таком случае это день назад
        report_end_day = datetime.datetime.now().date() - datetime.timedelta(days=1)
        day = report_end_day.day
        check_days = report_end_day

        chosen_days = []
        chosen_days_str = []

        # Например цикл начался с 19.04.2022, значит цикл будет продолжатся до 19.03.2022
        while True:
            chosen_days.append(check_days)
            chosen_days_str.append(check_days.strftime('%d.%m.%Y'))

            check_days -= datetime.timedelta(days=1)

            # Если цикл начался с 19.04.2022, значит цикл остановиться в 19.03.2022
            if check_days.day == day:
                break

        chosen_days.sort()
        chosen_days_str.sort()

    # Если админ хочет не месяц а несколько дней (который сам же указал: От 1-30 дней)
    else:
        pass

    # Create a workbook and add a worksheet.
    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet()

    # Создаем форматы для ячеек загаловок
    title_format = workbook.add_format({'bold': True, 'bg_color': '#82d513'})
    fio_format = workbook.add_format({'bold': True, 'bg_color': '#73a0d0'})
    # Формат для сталбцов: "Дата\n Приход\n Уход\n Опоздание\n Ранний уход..."
    data_field_format = workbook.add_format({'bold': True, 'bg_color': '#c0829f'})

    row = 2

    # Создаем титульную часть excel файла. Сперва добавим отступ чтобы текст был в середине экрана
    title = ' ' * 124 + config['excel']['title']

    # Запишем титульную часть документа
    worksheet.merge_range(row, 0, row, 31, title, title_format)
    # Перейдем на следующую строку
    row += 1

    # Создаем msg типа: "С: 2022-04-01 до: 2022-04-30"
    end_date = chosen_days_str[-1]
    start_date = chosen_days_str[0]
    date_str = f"{' ' * 132}С: {start_date} до: {end_date}"

    # Запишем промежуток: "С: 2022-04-01 до: 2022-04-30"
    worksheet.merge_range(row, 0, row, 31, date_str, title_format)
    # Перейдем на следующую строку
    row += 2

    # Получаем список всех рабочих(who=control): [(ID, name, Who, chat_id), ...]
    all_workers = sql_handler.get_all_workers()

    # В excel отчете у каждого будет свой отдельный блок.
    # for worker in [[31, 'rixsimov']]:
    for worker in all_workers:
        # Получаем все данные сотрудника за выбранный срок
        worker_report = WorkerReport(worker[0], chosen_days, chosen_days_str)

        # # Создаем первую строку блока сотрудника: "ФИО сотрудника:  first_name last_name"
        worker_name_row = f"{config['excel']['worker_name']}  {worker[1]}"
        # Полученный данные запишем в excel файл
        worksheet.merge_range(row, 0, row, 31, worker_name_row, fio_format)
        row += 1

        # # Создааем вторую строку блока сотрудника: "Дата: 12.02.2022, 13.02.2022, ..."
        worksheet.write(row, 0, config['excel']['date'], data_field_format)
        worksheet.write_row(row, 1, chosen_days_str)
        row += 1

        # Указываем имя стобца а потом данные которые нужно записать в excel
        all_blocks = [
            [config['excel']['came'], worker_report.in_history_str],
            [config['excel']['leave'], worker_report.out_history_str],
            [config['excel']['late'], worker_report.late_history],
            [config['excel']['early_leave'], worker_report.early_leaved_history],
            [config['excel']['missed_days'], worker_report.missed_days_history],
            [config['excel']['comments'], worker_report.comments],
            [config['excel']['locations'], worker_report.locations]
        ]

        # # Создаем блоки на основе all_blocks и записываем в excel
        for block in all_blocks:
            worksheet.write(row, 0, block[0], data_field_format)
            # Сортируем по ключу (так как ключ это date объект) и получаем только значения
            sorted_data = collections.OrderedDict(sorted(block[1].items())).values()
            worksheet.write_row(row, 1, sorted_data)
            row += 1

        # Между каждый сотрудником будет одна пустая строка в excel файле
        row += 1

    # Сохнарим созданный excel файл
    workbook.close()


async def schedule_jobs(dp):
    scheduler.add_job(excel_report_creator_first_type('month'), 'cron', hour=0, minute=0, args=(dp,))
    # scheduler.add_job(excel_report_creator_second_type('month'), 'cron', hour=0, minute=0, args=(dp,))


excel_report_creator_first_type('month')
