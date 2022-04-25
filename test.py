Traceback (most recent call last):
  File "/home/myadmin/test/vik_bot/venv/lib/python3.9/site-packages/apscheduler/executors/base_py3.py", line 30, in run_coroutine_job
    retval = await job.func(*job.args, **job.kwargs)
  File "/home/myadmin/test/vik_bot/checkup.py", line 94, in check_users_in_logs
    await send_notification_to_latecomer(dp, user)
  File "/home/myadmin/test/vik_bot/checkup.py", line 153, in send_notification_to_latecomer
    report_id = sql_handler.report_creator(latecomer_info[0])
  File "/home/myadmin/test/vik_bot/sql_handler.py", line 276, in report_creator
    cursor.execute("""INSERT INTO "report"(id, user_id, date) VALUES(?, ?, ?, ?);""",
KeyboardInterrupt
