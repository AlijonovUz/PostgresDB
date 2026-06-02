class ForeignKeyRelation:
    def __init__(self, field_name, related_model):
        self.field_name = field_name
        self.related_model = related_model

    def __get__(self, instance, owner):
        if instance is None:
            return self

        fk_value = getattr(instance, self.field_name, None)
        if fk_value is None:
            return None

        return self.related_model.find(fk_value)

    def __set__(self, instance, value):
        if value is not None:
            setattr(instance, self.field_name, getattr(value, value.__class__.get_pk_name()))
        else:
            setattr(instance, self.field_name, None)


class ReverseRelation:
    """
    Birga-ko'p (One-to-Many) va yakkama-yakka (One-to-One) teskari bog'lanish.
    Misol uchun: user.post_set.all(), user.post_set.filter(), user.post_set.update(), user.post_set.delete()
    """
    def __init__(self, related_model, fk_name, is_one_to_one=False):
        self.related_model = related_model
        self.fk_name = fk_name
        self.is_one_to_one = is_one_to_one

    def __get__(self, instance, owner):
        if instance is None:
            return self

        pk_name = instance.__class__.get_pk_name()
        pk_value = getattr(instance, pk_name, None)
        
        qs = self.related_model.filter(**{self.fk_name: pk_value})
        
        if self.is_one_to_one:
            return qs.first()

                                                                               
        def create(**kwargs):
            kwargs[self.fk_name] = pk_value
            return self.related_model.create(**kwargs)
        
        qs.create = create
        qs.create = create
        return qs

    def __set__(self, instance, value):
        raise AttributeError("Teskari bog'lanishni to'g'ridan-to'g'ri o'zgartirib bo'lmaydi.")


class AsyncForeignKeyRelation:
    def __init__(self, field_name, related_model):
        self.field_name = field_name
        self.related_model = related_model

    def __get__(self, instance, owner):
        if instance is None:
            return self

        fk_value = getattr(instance, self.field_name, None)
        if fk_value is None:
            return None

        return self.related_model.find(fk_value)

    def __set__(self, instance, value):
        if value is not None:
            setattr(instance, self.field_name, getattr(value, value.__class__.get_pk_name()))
        else:
            setattr(instance, self.field_name, None)


class AsyncReverseRelation:
    def __init__(self, related_model, fk_name, is_one_to_one=False):
        self.related_model = related_model
        self.fk_name = fk_name
        self.is_one_to_one = is_one_to_one

    def __get__(self, instance, owner):
        if instance is None:
            return self

        pk_name = instance.__class__.get_pk_name()
        pk_value = getattr(instance, pk_name, None)
        
        qs = self.related_model.filter(**{self.fk_name: pk_value})
        
        if self.is_one_to_one:
            import asyncio
            return asyncio.create_task(qs.first())

        async def create(**kwargs):
            kwargs[self.fk_name] = pk_value
            return await self.related_model.create(**kwargs)
            
        qs.create = create
        qs.create = create
        return qs

    def __set__(self, instance, value):
        raise AttributeError("Teskari bog'lanishni to'g'ridan-to'g'ri o'zgartirib bo'lmaydi.")


class ManyToManyRelation:
    """
    Ko'pga-ko'p (Many-to-Many) to'g'ri va teskari bog'lanish boshqaruvchisi.
    Misol uchun: user.groups.add(group_id), user.groups.all(), user.groups.remove(), user.groups.clear()
    """
    def __init__(self, target_model, through_table, source_col, target_col, is_async=False):
        self.target_model = target_model
        self.through_table = through_table
        self.source_col = source_col
        self.target_col = target_col
        self.is_async = is_async

    def __get__(self, instance, owner):
        if instance is None:
            return self
            
        pk_name = instance.__class__.get_pk_name()
        pk_value = getattr(instance, pk_name, None)
        
                                                                  
        join_clause = [(
            "INNER JOIN", 
            self.through_table, 
            f"{self.target_model.table}.{self.target_model.get_pk_name()} = {self.through_table}.{self.target_col}"
        )]
        qs = self.target_model.filter(**{f"{self.through_table}.{self.source_col}": pk_value})
        qs._join = join_clause
        
        db = instance.__class__.db
        
        if self.is_async:
            async def add(*target_ids):
                values = [[pk_value, t_id] for t_id in target_ids]
                await db.insert_many(self.through_table, f"{self.source_col}, {self.target_col}", values)
                
            async def remove(*target_ids):
                                                       
                placeholders = ", ".join(f"${i+2}" for i in range(len(target_ids)))
                sql = f"DELETE FROM {self.through_table} WHERE {self.source_col} = $1 AND {self.target_col} IN ({placeholders})"
                await db._manager(sql, pk_value, *target_ids, commit=True)
                
            async def clear():
                sql = f"DELETE FROM {self.through_table} WHERE {self.source_col} = $1"
                await db._manager(sql, pk_value, commit=True)
                
            qs.add = add
            qs.remove = remove
            qs.clear = clear
            
        else:
            def add(*target_ids):
                values = [(pk_value, t_id) for t_id in target_ids]
                db.insert_many(self.through_table, f"{self.source_col}, {self.target_col}", values)
                
            def remove(*target_ids):
                placeholders = ", ".join(["%s"] * len(target_ids))
                sql = f"DELETE FROM {self.through_table} WHERE {self.source_col} = %s AND {self.target_col} IN ({placeholders})"
                params = [pk_value] + list(target_ids)
                conn = db.pool.getconn()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(sql, tuple(params))
                        conn.commit()
                finally:
                    db.pool.putconn(conn)
                    
            def clear():
                sql = f"DELETE FROM {self.through_table} WHERE {self.source_col} = %s"
                conn = db.pool.getconn()
                try:
                    with conn.cursor() as cursor:
                        cursor.execute(sql, (pk_value,))
                        conn.commit()
                finally:
                    db.pool.putconn(conn)
                    
            qs.add = add
            qs.remove = remove
            qs.clear = clear
            
            qs.clear = clear
            
        return qs

    def __set__(self, instance, value):
        raise AttributeError("ManyToMany bog'lanishni to'g'ridan-to'g'ri o'zgartirib bo'lmaydi. .add() yoki .remove() ishlating.")