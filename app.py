from flask import Flask, render_template, redirect, url_for, request, g
from flask_wtf import FlaskForm
from flask_bootstrap import Bootstrap
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3


app = Flask(__name__)
app.secret_key = 'secret string'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

Bootstrap(app)

DATABASE = 'library.db'
BORROW_CAPACITY = 2

class User(UserMixin):
    def __init__(self, id: str, username: str, admin: bool):
        self.id = id
        self.username = username
        self.admin = admin

@login_manager.user_loader
def load_user(user_id):
    cur = sqlite3.connect('library.db').cursor()
    if user_id == "0":
        print("admin")
        res = cur.execute("SELECT * FROM Admin WHERE Id = ?", (user_id,))
    else:
        res = cur.execute("SELECT * FROM Student WHERE Id = ?", (user_id,))
    result = res.fetchone()
    if result:
        return User(result[0], result[1], (user_id==0))
    return None


def get_db():
    """set up database connection"""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.before_request
def connect_database():
    get_db()


@app.route("/")
def main():
    return render_template('main.html')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    administration = BooleanField('I am administrator')
    submit = SubmitField('Log in')


# Login
@app.route("/login", methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():

        # user parameters
        username = form.username.data
        password = form.password.data
        admin = form.administration.data
        
        # database cursor
        cur = get_db().cursor()

        # process data
        if admin:
            res = cur.execute("SELECT Id FROM Admin WHERE Name = ? AND Password = ?", (username, password))
            result = res.fetchone()
            if result:
                user = User(id=result[0], username=username, admin=True)
                login_user(user)
                return redirect(url_for('menu', admin=1))
            else:
                form.password.errors.append("Invalid name or password!")
        else:
            res = cur.execute("SELECT Id FROM Student WHERE Name = ? AND Password = ?", (username, password))
            result = res.fetchone()
            if result:
                user = User(id=result[0], username=username, admin=False)
                login_user(user)
                return redirect(url_for('menu'))
            else:
                form.password.errors.append("Invalid name or password!")

    return render_template('login.html', form = form)


class LookUpForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])


# Student Manu
@app.route('/menu')
@login_required
def menu():
    auth = request.args.get('admin')
    if auth:
        return render_template('admin.html')
    
    # get user parameters
    search_query = request.args.get('search', '')
    title = request.args.get('title')
    author = request.args.get('author')

    # database connection
    con = get_db()
    cur = con.cursor()

    message = ("", "")
    error = ("", "")
    borrowed = ("", "")
    full = ("", "")
    if search_query:
        res = cur.execute("SELECT * FROM Book WHERE Title = ?", (search_query, )).fetchall()
        if res:
            return render_template('student.html', books=res, message=message, error=error, borrowed=borrowed, full=full)
        else:
            return render_template('student.html', not_found=1)
    elif title:
        # get book information
        (bookID, bookNum) = cur.execute("SELECT BookId, AvailableCopies FROM Book WHERE Title = ? AND Author = ?", (title, author)).fetchone()
        borrow_count = cur.execute("SELECT BorrowCount FROM Student WHERE Id = ?", (current_user.id,)).fetchone()
        current_record = cur.execute("SELECT * FROM Record WHERE Id = ? AND BookId = ?", (current_user.id, bookID)) # check whether the user has borrowed the book
        if current_record.fetchone():
            borrowed = (title, author)
        elif borrow_count[0] == BORROW_CAPACITY:
            full = (title, author)
        else:
            if bookNum:  # Still have available copies
                # add a record of borrow
                data = [current_user.id]
                data.append(bookID)
                cur.execute("INSERT INTO Record (Id, BookId) VALUES(?, ?)", data)

                # minus one available copy
                cur.execute("UPDATE Book SET AvailableCopies = AvailableCopies - 1 WHERE BookId = ?", (bookID,))

                # add one to the number of borrowed books
                cur.execute("UPDATE Student SET BorrowCount = BorrowCount + 1 WHERE Id = ?", (current_user.id,))

                con.commit() # commit changes
                message = (title, author)
            else:
                error = (title, author)
        res = cur.execute("SELECT * FROM Book WHERE Title = ?", (title, )).fetchall()
        return render_template('student.html', books=res, message=message, error=error, borrowed=borrowed, full=full)


    return render_template('student.html')


@app.route('/borrow')
@login_required
def borrow():
    title = request.args.get('title')
    author = request.args.get('author')

    # database connection
    con = get_db()
    cur = con.cursor()

    # ajust book information and return message
    message = ("", "")
    error = ("", "")
    borrowed = ("", "")
    full = ("", "")
    if title:
        # get book information
        (bookID, bookNum) = cur.execute("SELECT BookId, AvailableCopies FROM Book WHERE Title = ? AND Author = ?", (title, author)).fetchone()
        borrow_count = cur.execute("SELECT BorrowCount FROM Student WHERE Id = ?", (current_user.id,)).fetchone()
        current_record = cur.execute("SELECT * FROM Record WHERE Id = ? AND BookId = ?", (current_user.id, bookID)) # check whether the user has borrowed the book
        if current_record.fetchone():
            borrowed = (title, author)
        elif borrow_count[0] == BORROW_CAPACITY:
            full = (title, author)
        else:
            if bookNum:  # Still have available copies
                # add a record of borrow
                data = [current_user.id]
                data.append(bookID)
                cur.execute("INSERT INTO Record (Id, BookId) VALUES(?, ?)", data)

                # minus one available copy
                cur.execute("UPDATE Book SET AvailableCopies = AvailableCopies - 1 WHERE BookId = ?", (bookID,))

                # add one to the number of borrowed books
                cur.execute("UPDATE Student SET BorrowCount = BorrowCount + 1 WHERE Id = ?", (current_user.id,))

                con.commit() # commit changes
                message = (title, author)
            else:
                error = (title, author)

    # get books information
    books = cur.execute("SELECT * FROM Book").fetchall()
    return render_template('borrow.html', books=books, message=message, error=error, borrowed=borrowed, full=full)


@app.route('/return')
@login_required
def return_():
    title = request.args.get('title')
    author = request.args.get('author')
    print(title, author)

    # database connection
    con = get_db()
    cur = con.cursor()
    if title:
        # delete the record of borrow
        res = cur.execute("SELECT Recordid FROM Record, Book WHERE Record.BookId = Book.BookId AND Id = ? AND Title = ? AND Author = ?", (current_user.id, title, author)).fetchone()
        cur.execute("DELETE FROM Record WHERE RecordId = ?", res)  

        # add one to the available count
        cur.execute("UPDATE Book SET AvailableCopies = AvailableCopies + 1 WHERE title = ? AND Author = ?", (title, author))

        # minus one to the number of borrowed books
        cur.execute("UPDATE Student SET BorrowCount = BorrowCount - 1 WHERE Id = ?", (current_user.id,))

        con.commit()  # commit changes

    # get borrowed books
    books = cur.execute(f"""
                        SELECT Title, Author FROM Book, Record 
                        WHERE Book.BookId = Record.BookId and Record.Id = ?
                        """, (current_user.id,)).fetchall()
    
    return render_template('return.html', books=books)


class ChangePasswordForm(FlaskForm):
    password_pre = PasswordField('Previous Password', validators=[DataRequired()])
    password_new = PasswordField('New Password', validators=[DataRequired()])
    submit = SubmitField('Submit')


@app.route('/password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():

        # user parameters
        password_pre = form.password_pre.data
        password_new = form.password_new.data

        # database connection
        con = get_db()
        cur = con.cursor()

        # process data
        res = cur.execute("SELECT * FROM Student WHERE Id = ? AND Password = ?", (current_user.id, password_pre))
        if res.fetchone():
            cur.execute("UPDATE Student SET Password = ? WHERE Id = ?", (password_new, current_user.id))
            con.commit()
            return render_template('password.html', success = 1)
        else:
            form.password_pre.errors.append("Wrong password!")
    
    return render_template('password.html', form=form)


@app.route('/information')
@login_required
def information():
    
    # database connection
    cur = get_db().cursor()

    # get data
    (name, borrow_count, gender, telephone, major) = cur.execute("SELECT Name, BorrowCount, gender, telephone, major FROM Student Where Id = ?", (current_user.id,)).fetchone()
    return render_template('information.html', name=name, borrow_count=borrow_count, id=current_user.id, gender=gender, telephone=telephone, major=major)


@app.route('/record')
@login_required
def record():
    cur = sqlite3.connect('library.db').cursor()
    records = cur.execute("""SELECT Name, Title FROM Student, Book, Record
                             WHERE Student.Id = Record.Id and Book.BookId = Record.BookId""").fetchall()
    print(records)
    return render_template("record.html", records=records)


@app.route('/studentList')
@login_required
def student_list():

    # database connection
    cur = get_db().cursor()
    students = cur.execute("SELECT * FROM Student").fetchall()
    return render_template('student_list.html', students=students)


class AddReaderForm(FlaskForm):
    name = StringField("Student name", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    password_repeat = PasswordField("Repeat Password", validators=[DataRequired()])
    gender = StringField("Gender", validators=[DataRequired()])
    telephone = StringField("Telephone", validators=[DataRequired()])
    major = StringField("Major", [DataRequired()])
    submit = SubmitField("Submit")

@app.route('/addReader', methods=['GET', 'POST'])
@login_required
def add_reader():
    form = AddReaderForm()
    if form.validate_on_submit():
        name = form.name.data
        password = form.password.data
        gender = form.gender.data
        telephone = form.telephone.data
        major = form.major.data
        password_repeat = form.password_repeat.data
        if password != password_repeat:
            form.password_repeat.errors.append("The passwords are not the same!")
            return render_template('add_student.html', form=form)
        
        # database connection
        con = get_db()
        cur = con.cursor()
        res = cur.execute("SELECT * FROM Student Where Name = ?", (name, )).fetchone()
        if res:
            form.name.errors.append("This student information exists!")
            return render_template('add_student.html', form=form)
        cur.execute("INSERT INTO Student (Name, BorrowCount, Password, Gender, Telephone, Major) VALUES(?, ?, ?, ?, ?, ?)", (name, 0, password, gender, telephone, major))
        con.commit()
        return render_template('add_student.html', success=1)

    return render_template('add_student.html', form=form)


@app.route('/deleteReader')
@login_required
def delete_reader():
    id = request.args.get('id')

    # database connection
    con = get_db()
    cur = con.cursor()

    not_return = ""
    if id:
        res = cur.execute("SELECT BorrowCount FROM Student WHERE Id = ?", (id,)).fetchone()
        if res[0] != 0:
            not_return = id
        else:
            cur.execute("DELETE FROM Student WHERE Id = ?", (id,))
            con.commit()
    students = cur.execute("SELECT * FROM Student").fetchall()

    return render_template('delete_student.html', students=students, not_return=not_return)


@app.route('/bookList')
@login_required
def book_list():
    # database connection
    cur = get_db().cursor()
    books = cur.execute("SELECT * FROM Book").fetchall()
    return render_template('book_list.html', books=books)


class AddBookForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    author = StringField("Author", validators=[DataRequired()])
    total_copies = StringField("Total number of copies", validators=[DataRequired()])
    submit = SubmitField("Submit")


@app.route('/addBook', methods=['GET', 'POST'])
@login_required
def add_book():
    form = AddBookForm()
    if form.validate_on_submit():
        title = form.title.data
        author = form.author.data
        total_copies = form.total_copies.data
        
        # database connection
        con = get_db()
        cur = con.cursor()
        res = cur.execute("SELECT * FROM Book Where Title = ? AND Author = ?", (title, author)).fetchone()
        if res:
            form.title.errors.append("This book has been added exists!")
            return render_template('add_book.html', form=form)
        cur.execute("INSERT INTO Book (Title, Author, TotalCopies, AvailableCopies) VALUES(?, ?, ?, ?)", 
                    (title, author, total_copies, total_copies))
        con.commit()
        return render_template('add_book.html', success=1)

    return render_template('add_book.html', form=form)


@app.route('/deleteBook')
@login_required
def delete_book():
    title = request.args.get('title')
    author = request.args.get('author')

    # database connection
    con = get_db()
    cur = con.cursor()

    not_return = ""
    if title:
        (total_copies, available_copies) = cur.execute("""SELECT TotalCopies, AvailableCopies FROM Book 
                          WHERE Title = ? AND Author = ?""", (title, author)).fetchone()
        if total_copies != available_copies:
            not_return = (title, author)
        else:
            cur.execute("DELETE FROM Book WHERE Title = ? AND Author = ?", (title, author))
            con.commit()
    books = cur.execute("SELECT * FROM Book").fetchall()

    return render_template('delete_book.html', books=books, not_return=not_return)


class SetPasswordForm(FlaskForm):
    name = StringField("Student name", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    password_repeat = PasswordField("Repeat Password", validators=[DataRequired()])
    submit = SubmitField("Submit")


@app.route('/setPassword', methods=['GET', 'POST'])
@login_required
def set_password():
    form = SetPasswordForm()
    if form.validate_on_submit():
        name = form.name.data
        password = form.password.data
        password_repeat = form.password_repeat.data
        print(password)
        print(password_repeat)
        if password != password_repeat:
            form.password_repeat.errors.append("The passwords are not the same!")
            return render_template('set_password.html', form=form)
        
        # database connection
        con = get_db()
        cur = con.cursor()
        res = cur.execute("SELECT * FROM Student Where Name = ?", (name, )).fetchone()
        if res:
            cur.execute("UPDATE Student SET Password = ? WHERE Name = ?", (password, name))
            con.commit()
            return render_template('set_password.html', success=1)
        else:
            form.name.erros.append("The student does not exist!")

    return render_template('set_password.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.teardown_request
def teardown_request(exception):
    """close connection after request"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
    return None  


