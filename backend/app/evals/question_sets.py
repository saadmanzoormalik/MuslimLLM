from psycopg import Connection


def list_question_sets(conn: Connection):
    return conn.execute(
        """
        select qs.*,
               count(q.id) as question_count
        from eval_question_sets qs
        left join eval_questions q on q.question_set_id=qs.id
        group by qs.id
        order by qs.updated_at desc
        """
    ).fetchall()


def list_questions(conn: Connection, question_set_id: str | None = None):
    return conn.execute(
        """
        select q.*, qs.name as question_set_name
        from eval_questions q
        left join eval_question_sets qs on qs.id=q.question_set_id
        where (%s::uuid is null or q.question_set_id=%s::uuid)
        order by q.created_at asc
        """,
        (question_set_id, question_set_id),
    ).fetchall()
