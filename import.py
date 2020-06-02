import os

from csv import reader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session


if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL isn't set")

# set up the db
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


books = reader(open("books.csv"))
next(books)

# importing books to the db
for isbn, title, author, year, book_cover_url in books:
    # add leading zeroes to the isbn if it's less than 10
    i = len(isbn)
    while i < 10:
        isbn = '0' + isbn
        i += 1
    db.execute("INSERT INTO books (isbn, title, author, year, book_cover_url) VALUES (:isbn, :title, :author, :year, :book_cover_url)",
                {"isbn": isbn, "title": title, "author": author, "year": int(year), "book_cover_url": book_cover_url})
db.commit()
print("Imported all the books successfully! :D")    


