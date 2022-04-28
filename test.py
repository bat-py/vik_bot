try:
  cursor.execute("INSERT INTO user (user_id, first_name) VALUES (%s, %s)", (user_id, first_name))
  connection_2.commit()
except:
  last_name = message.from_user.last_name

  if last_name:
    try:
      cursor.execute("INSERT INTO user (user_id, first_name) VALUES (%s, %s)", (user_id, last_name))
      connection_2.commit()
    except:
      cursor.execute("INSERT INTO user (user_id, first_name) VALUES (%s, %s)", (user_id, "?????"))
      connection_2.commit()
  else:
    cursor.execute("INSERT INTO user (user_id, first_name) VALUES (%s, %s)", (user_id, "?????"))
    connection_2.commit()