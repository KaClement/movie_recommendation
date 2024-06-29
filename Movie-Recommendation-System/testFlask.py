from forms import RegisterForm
from forms import SearchForm
from forms import LoginForm
from forms import RatingForm
from forms import CommentForm
from flask import Flask, render_template, flash, session, logging, request
from flask import redirect, url_for
import pymysql
from passlib.hash import sha256_crypt
import mysql.connector
import tmdbsimple as tmdb
from functools import wraps
import pandas as pd
import random
import csv
from scipy import sparse

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'admin'

# #CONFIG MYSQL
db = pymysql.connect(host='localhost', user='root', password='', database= "projett1")


# -- Credentials --
tmdb.API_KEY  = "1ff6da82b584d884cb4d194786c44ca8"


@app.route('/')
def home():
    
    return render_template('home.html')

# --- Login System mySQL DB check || Register create row in table DB ---
@app.route('/register', methods=['GET', 'POST'])
def signup():
    form = RegisterForm(request.form)
    
    if request.method == 'POST' and form.validate():
        cursor = db.cursor()
        username = form.username.data
        mail = form.mail.data
        password = sha256_crypt.encrypt(str(form.password.data))
        birthDate = form.dateOfBirth.data
        favActors = form.favActors.data
        favDirectors = form.favDirectors.data
        # Insert form data into database
        query = "INSERT INTO client (IDclient,Username,DateOfBirth, password, mail, favActors, favDirectors) VALUES (%s,%s, %s, %s, %s, %s, %s)"
        new_user_id = random.randint(20000,50000)
        values = (new_user_id ,username, birthDate, password, mail, favActors, favDirectors)
        cursor.execute(query, values)
        db.commit()
        # Close database connections
        cursor.close()
        flash('You are now registered')
        
        return redirect(url_for('login'))
    else:
        print(form.errors)
        return render_template('register.html', form=form)
    
last_user =""
@app.route('/login', methods=['GET', 'POST'])
def login():
    global last_user
    form = LoginForm()
    if request.method == 'POST':
        #get form fields-
        username = request.form['username']
        password_candidate = request.form['password']
        last_user = username
        #create a cursor : 
        cursor = db.cursor()
        #get user by username : 
        cursor.execute('SELECT * FROM client WHERE username = %s', [username])
        data = cursor.fetchone()
        if data is not None: # if any rows found
            #get stored hash
            password = data[3]
            user_id = (data[0],)
            #comapre passowrds : 
            if sha256_crypt.verify(password_candidate, password):
                session['logged_in'] = True
                session['username'] = username
                session['user_id'] = user_id
                flash('Logged In ', 'success')
                db.commit()
                cursor.close()
                
                return render_template('home.html')
            else: 
                app.logger.info('Password error')
            db.commit()
            cursor.close()
            
        else:
            app.logger.info('No USER')
            db.commit()
            cursor.close()
            
            return render_template('login.html', form = form)
    return render_template('login.html', form = form)

#check if user logged in 
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('unauthorized, please login', 'danger')
            return redirect(url_for('login'))
    return wrap

#logout
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged Out", 'success')
    return redirect(url_for('login'))


def add_users():
    cursor = db.cursor()
    data = pd.read_csv('ratings.csv')
    data = data[['userId']]
    for index, row in data.iterrows():

        userId = int(row['userId'])
        cursor = db.cursor()
        query = "SELECT * FROM client WHERE IDclient = %s"
        cursor.execute(query, [userId])
        result = cursor.fetchone()

        if cursor.rowcount ==0:
            query = "INSERT INTO client (IDclient, Username, DateOfBirth, password, mail) VALUES (%s, %s, %s, %s, %s)"
            values = (userId, "Skynet", 2000, "terminator", "kclem0712@gmail.com")
            cursor.execute(query, values)
            db.commit()
           
        else:
            pass
        
        cursor.close()

    db.close()

def add_movies():
    
    data = pd.read_csv('movies.csv')
    
    data = data[['movieId','title','genres']]
    for index, row in data.iterrows():
        cursor = db.cursor()
        movieId = int(row['movieId'])
        title = row['title']
        date = title[-5:-1]
        #get ratings on imdb
        search = tmdb.Search()
        response = search.movie(query = title)
        rating = 'N/A'
        
        if search.results:
            movie_id = search.results[0]['id']
            movie = tmdb.Movies(movie_id)
            response = movie.info()
            rating = response['vote_average']
        
        genres = row['genres']
        
        query = "INSERT INTO film (IDfilm, Name, Date, NoteAvg ,Genre) VALUES (%s,%s,%s,%s,%s)"
        values = (movieId, title, date, rating, genres )
        cursor.execute(query, values)
        db.commit()
        cursor.close()
    db.close()


def add_ratings():
    data = pd.read_csv('ratings.csv')
    data = data[['userId', 'movieId','rating']]
    for index, row in data.iterrows():
        cursor = db.cursor()
        userId = row['userId']
        movieId = row['movieId']
        rating = row['rating']
        query = "INSERT INTO userchoice (IDclient, IDFilm, Note, Comment) VALUES (%s, %s, %s, %s)"
        values = (userId, movieId, rating, " ")
        cursor.execute(query, values)
        db.commit()
        # Close database connections
        cursor.close()
    db.close()#curso object


last_movie = ""
last_movie_date = ""
last_rating =""
number_vote = ""
# --- Search for a movie -> it displays title, actors, directors, image, ratings, comment section & note ---
@app.route('/search', methods = ['GET', 'POST'])
def search():
    global last_movie
    global last_movie_date
    global last_user
    global last_rating
    global number_vote

    form = SearchForm()
    form_2 = RatingForm()
    comment_form = CommentForm()
    
    if form.validate_on_submit():
        title = form.movie.data
        search = tmdb.Search()
        response = search.movie(query=title)

        if len(search.results) > 0:
            movie_id = search.results[0]['id']
            
            movie = tmdb.Movies(movie_id)
            response = movie.info(append_to_response='credits')
            last_movie = response.get('title')
            director_info = next(
                (person for person in response['credits']['crew'] if person['job'] == 'Director'), None)
            director_name = director_info['name'] if director_info else 'Unknown'
            actor_names = [person['name'] for person in response['credits']['cast'][:3]]
            description = response['overview']
            release_date = response['release_date']
            last_movie_date = release_date

            genres = response['genres']
            genre_name = [genre['name'] for genre in genres]
            
            rating = response['vote_average']
            last_rating = rating
            # check average rating of movie in database is not0, if not then show the database average rating

            count_vote = response['vote_count']

            number_vote = count_vote
            poster_path = response['poster_path']
            poster_url = f"https://image.tmdb.org/t/p/w500/{poster_path}"

            movie_1 = last_movie + " (" +last_movie_date[:-6] + ")"
            id_of_movie = fetch_id_movie(movie_1)
            
            # check average rating of movie in database is not0, if not then show the database average rating
            accurate_rating = getNoteAvg(id_of_movie)
            print("accurate rating :")
            print(accurate_rating)
            if accurate_rating[0] !=0:
                rating = accurate_rating[0]

            id_user = session.get('user_id')
            print(id_user)
            
            if id_user is not None:

                checking_note = checkingUserNote(id_user, id_of_movie)
            else:
                pass


            vote_counter = getnoteCount(id_of_movie)
            if vote_counter is None : 
                    vote_counter = number_vote
                    addVoteCount(id_of_movie,number_vote)
   
            id_of_movie = (id_of_movie,)


            #if movie in database :
            comments = fetch_comments(id_of_movie)

            if id_user is not None:
                return render_template('search.html', form=form, form_2=form_2, comment_form=comment_form,
                                   title=response.get('title'), director=director_name, actors=actor_names,
                                   description=description, release_date=release_date, rating= rating, checking_note=checking_note, genre_name=genre_name, vote_counter = vote_counter,
                                   poster_url=poster_url, comments=comments)
            else:
                return render_template('search.html', form=form, form_2=form_2, comment_form=comment_form,
                                   title=response.get('title'), director=director_name, actors=actor_names,
                                   description=description, release_date=release_date, vote_counter=vote_counter, genre_name=genre_name, rating = rating,
                                   poster_url=poster_url, comments=comments)
                      
    
    if form_2.validate_on_submit():
                note = form_2.note.data
                
              

                id_user = session.get('user_id')
                
                #get the movie ID
                movie = last_movie + " (" +last_movie_date[:-6] + ")"
                id_film = fetch_id_movie(movie)

                #if in the film table, the noteAvg is 0 then add API rating in the table:
                noteAvgChange(id_film, last_rating)

                #get the noteCount of the movie in the database : 
                noteCount = getnoteCount(id_film)
                if noteCount is None : 
                        addVoteCount(id_film,count_vote)


                #add everything to the userchoice table :
                if id_film is not None:
                    cursor_3 = db.cursor()
                    query = "INSERT INTO userchoice (IDclient,IDfilm, Note, Comment) VALUES (%s, %s, %s, NULL)"
                    
                    values = (id_user[0], id_film[0], note)
                    cursor_3.execute(query, values)
                    db.commit()
                    cursor_3.close()

                    #calculate new average rating of that movie : 
                    movie_rating = getNoteAvg(id_film)

                    new_average_rating = noteAvgCalc(movie_rating, noteCount, note)
                    
                    #add new average rating of that movie to the userchoice table:
                    cursor_3 = db.cursor()
                    query = "UPDATE film SET NoteAvg = %s WHERE IDfilm = %s"
                    values = (new_average_rating,id_film[0])
                    cursor_3.execute(query, values)
                    db.commit()
                    cursor_3.close()


                    # add 1 to the note_count of the movie in the film table  : 
                    cursor_3 = db.cursor()
                    query = "UPDATE film SET NoteCount = NoteCount + 1 WHERE IDfilm = %s"
                    values = (id_film[0],)
                    cursor_3.execute(query, values)
                    db.commit()
                    cursor_3.close()

                   
                        
                    flash('Rating submitted successfully')
                    return render_template('search.html', form=form, form_2=form_2, note=note, comment_form=comment_form)
                else:
                    print("FAILED")
                    flash('Rating failed')
                    return render_template('search.html', form=form, form_2=form_2, note=note, comment_form=comment_form)
                

    if comment_form.validate_on_submit():
                comment = comment_form.comment.data


                movie = last_movie + " (" +last_movie_date[:-6] + ")"
                print(movie)
                #with the movie title, fetch the movie Id in the film table.
                id_film =  fetch_id_movie(movie)
                print("ID FILM : ")
                print(id_film)
               
             

                id_user = session.get('user_id')
                # id_user = (id_user,)
                
                if id_film[0] and id_user[0] is not None:
                    #add to the userchoice table the comment : 
                    cursor_3 = db.cursor()
                    query = "INSERT INTO userchoice (IDclient,IDfilm, Note, Comment) VALUES (%s, %s, NULL, %s)"
                    values = (id_user[0], id_film[0], comment)
                    cursor_3.execute(query, values)
                    db.commit()
                    cursor_3.close()
                    
                    # with the ID, scan the userchoice table,  fecth the comments associated with that movie ID
                    comments = fetch_comments((id_film,))
                    flash('Comment submitted successfully')
                    return render_template('search.html', form=form, form_2=form_2, comment=comment, comments=comments,
                                       comment_form=comment_form)
                else:
                    return render_template('search.html', form=form, form_2=form_2, comment=comment,
                                       comment_form=comment_form)
                
                
    
    else: print('No movie found.')
    
    return render_template('search.html', form=form, form_2=form_2, comment_form=comment_form)

def add_movie_searched(movie):
    cursor_3 = db.cursor()
    query = "INSERT INTO film (IDfilm,Name, NoteAvg, Genre, Date) VALUES (%s, %s, %s, NULL,%s)"
    id_film = random.randint(20000,50000)
   
    name = movie
    date = " (" +last_movie_date[:-6] + ")"
    print(date)
    NoteAvg = last_rating
    values = (id_film, name,NoteAvg,date )
    cursor_3.execute(query, values)
    db.commit()
    cursor_3.close()
    print("Movie added to the database with this ID :")
    print(id_film)
    return id_film

def fetch_id_movie(movie):
    cursor = db.cursor()
    print(movie)
    cursor.execute('SELECT IDfilm FROM film WHERE Name = %s', [movie])
    id_film = cursor.fetchone()
    db.commit()
    cursor.close()
   
    if id_film is None:
        id_film_2 = add_movie_searched(movie)
        return (id_film_2,) #add it to the database and recursively search for it
    else:
        return id_film

#Fonction pour chercher tout les commentaires qu'il y a sur un film dans userchoice en se basant sur son ID
def fetch_comments(id_film):
    cursor= db.cursor()
    query = "SELECT Comment FROM userchoice WHERE IDfilm = %s AND Comment IS NOT NULL"
    cursor.execute(query, (id_film[0]))
    comments = cursor.fetchall()
    db.commit()
    cursor.close()
    return [comment[0] for comment in comments if comment[0] is not None]

# Erreur dans la table userchoice, column comment, on avait des " " espace vide au lieu de NULL   
def addNuLL():
    cursor = db.cursor()
    query = "UPDATE userchoice SET Comment = NULL WHERE Comment = ' '"
    try:
        cursor.execute(query)
        db.commit()
        cursor.close()
        db.close()
    except Exception as e:
        print(f"Error occurred: {e}")

#fonction pour ajouter les voteCount de chaque film dans notre database base on the api :
def addVoteCount(id_film,numbervote):
    cursor_3 = db.cursor()
    query = "UPDATE film SET NoteCount = %s  WHERE IDfilm = %s"
    values = (numbervote,id_film[0])
    cursor_3.execute(query, values)
    db.commit()
    cursor_3.close()
    return numbervote

def getnoteCount(id_film):
    cursor = db.cursor()
    cursor.execute('SELECT NoteCount FROM film WHERE IDfilm = %s', [id_film[0]])
    note = cursor.fetchone()
    db.commit()
    cursor.close()
    return note[0]


def noteAvgChange(id_film, last_rating):
    
    cursor_2 =db.cursor()
    query = "SELECT NoteAvg FROM film  WHERE IDfilm =%s"
    values = (id_film[0],)
    cursor_2.execute(query, values)
    result = cursor_2.fetchone()
    print("noteAvgChange() : ")
    print(result)
    db.commit()
    cursor_2.close()
    cursor_3 = db.cursor()

    if result[0] == 0 :
        query = "UPDATE film SET NoteAvg = %s  WHERE IDfilm = %s"
        values = (last_rating ,id_film[0])
        cursor_3.execute(query, values)
        db.commit()
        cursor_3.close()
    return

def checkingUserNote(id_user, id_film):
    #if user already rated a movie, then form not availble
    cursor = db.cursor()
    query='SELECT Note FROM userchoice WHERE IDclient = %s AND IDfilm = %s'
    values = (id_user[0], id_film[0])
    cursor.execute(query,values)
    note = cursor.fetchone()
    
    cursor.close()
    
    

    
    if note is None:
        return None
    else:
        return note[0]


def getNoteAvg(id_film):
    cursor_2 =db.cursor()
    query = "SELECT NoteAvg FROM film  WHERE IDfilm =%s"
    values = (id_film[0],)
    cursor_2.execute(query, values)
    result = cursor_2.fetchone()
    db.commit()
    cursor_2.close()
    print("getNoteAvg() : ")
    print(float(result[0]))
    return result

def noteAvgCalc(last_rating, noteCount, note):
    #double the note in the userchoice table
    print("Input to noteAvgCalc(): LAST RATING VALUE=  ")
    print(last_rating)
    last_rating = float(last_rating[0])
    noteCount = float(noteCount)
    note = float(note)
    print("Before computation: AVGating=" )
    print(last_rating)
    new_average_rating = ((last_rating * noteCount) + note) / (noteCount + 1)
    print("After computation: AVGating=: ")
    print(new_average_rating)
    return new_average_rating
    
                        
# --- Get a recommendation -> based on prefered genre, favourite actors, favourite director

def csvRecommendation():
    cursor = db.cursor()
    # Execute the SQL query
    query = "SELECT uc.IDclient, uc.IDfilm, uc.Note, f.Name FROM userchoice uc JOIN film f ON uc.IDfilm = f.IDfilm"
    cursor.execute(query)

    
    rows = cursor.fetchall()

    
    csv_file = "output.csv"


    with open(csv_file, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["IDclient", "IDfilm", "Note", "Name"])  # Write the header
        writer.writerows(rows)  # Write the rows

    # Close the cursor and database connection
    cursor.close()
    
    return

@app.route('/recommendation')

def AlgoRecommendation():
    
    id_user = session.get('user_id')
    print(id_user)
    global corrMatrix
    csvRecommendation()
    ratings = pd.read_csv("./output.csv")
    userRatings = ratings.pivot_table(index=['IDclient'],columns=['Name'],values='Note')
    userRatings = userRatings.dropna(thresh=10, axis=1).fillna(0,axis=1)
    corrMatrix = userRatings.corr(method='pearson')
    print("Correlation Matrix : ")
    print(corrMatrix.head())
    
    #tout les films noté par id_user
    
    wow = get_user_taste(id_user)
    print("user taste :")
    print(wow)
    similar_movies = pd.DataFrame()
    
    for _, row in wow.iterrows():
        Name = row['Name']
        note = row['note']
        result = get_similar_movies(Name, note)
        if result is not None:
            similar_movies = pd.concat([similar_movies,result], ignore_index=True)

   
    similar_movies = similar_movies.sort_values(by='Similarity', ascending=False)   
    # Get movie titles as lists
    
    wow_movie_titles = wow['Name'].tolist()

    print("Similar Movies : ")
    print(similar_movies.head(20))
    movies_rec = similar_movies.head(15)
    movies_rec = movies_rec['Movie'].tolist()

    # Filter similar movie titles
    filtered_movie_titles = [movie for movie in movies_rec if movie not in wow_movie_titles]
    movies_rec = filtered_movie_titles
    print("Filtered movie")
    print(movies_rec)

    movies_rec = delete_dates(movies_rec)
    print("Favourite actor : ")
    actor_movie_list  = get_favActor_movie(id_user)
    print(actor_movie_list)
    print("Favourite director : ")
    
    director_movie_list = get_favDirector_movie(id_user)

    
    return render_template('recommendation.html', director_movie_list=director_movie_list, actor_movie_list=actor_movie_list, movies_rec = movies_rec, get_movie_poster= get_movie_poster)

def get_favActor_movie(id_user):
    
    #check in database of user if he has favourite actor
    cursor = db.cursor()
    query='SELECT favActors FROM client WHERE IDclient = %s'
    cursor.execute(query, (id_user[0],))
    favActor = cursor.fetchone()
    cursor.close()
    if favActor is not None:
        favActor = favActor[0]
        print(favActor)
        search = tmdb.Search()
        response = search.person(query=favActor)
        if search.results:
            person_id = search.results[0]['id']
            person = tmdb.People(person_id)
            credits = person.movie_credits()

            if 'cast' in credits:
                movies = credits['cast']
                filtered_movies = [movie for movie in movies if movie['vote_count'] > 1000]
        
                sorted_movies = sorted(filtered_movies, key=lambda movie: movie['vote_average'], reverse=True)
                top_movies = sorted_movies[:4]
                top_movie_titles = [movie['title'] for movie in top_movies]
                return top_movie_titles
        else:
            pass
    else:
        return None


def get_favDirector_movie(id_user):
    #check in database of user if he has favourite actor
    cursor = db.cursor()
    query='SELECT favDirectors FROM client WHERE IDclient = %s'
    cursor.execute(query, (id_user[0],))
    favDirector = cursor.fetchone()
    cursor.close()
    if favDirector is not None:
        favDirector = favDirector[0]
        print(favDirector)
        search = tmdb.Search()
        response = search.person(query=favDirector)

        if search.results:
            director_id = search.results[0]['id']
            director = tmdb.People(director_id)
            credits = director.movie_credits()

            if 'crew' in credits:
                movies = credits['crew']
               
                # Filter movies where the director matches
                director_movies = [movie for movie in movies if movie['department'] == 'Directing']
                
                # Sort movies by vote average in descending order
                sorted_movies = sorted(director_movies, key=lambda movie: movie['vote_average'], reverse=True)
                top_movies = sorted_movies[:4]
                top_movie_titles = [movie['title'] for movie in top_movies]
                return top_movie_titles


    else:
        return None

def get_movie_poster(movie_title):
    search = tmdb.Search()
    response = search.movie(query=movie_title)

    if len(search.results) > 0:
        movie_id = search.results[0]['id']
        movie = tmdb.Movies(movie_id)
        response = movie.info(append_to_response='credits')
        poster_path = response['poster_path']
        poster_url = f"https://image.tmdb.org/t/p/w500/{poster_path}"
        return poster_url
    
    return None


def add_user_to_ratings(user_id, ratings_df, movie_ratings):
    # Create a new row for the user
    new_row = pd.DataFrame(columns=ratings_df.columns, index=[user_id])
    
    # Set the ratings for the movies the user has rated
    for movie_title, rating in movie_ratings:
        new_row[movie_title] = rating
    
    # Append the new row to the ratings DataFrame
    ratings_df = pd.concat([ratings_df, new_row])
    
    return ratings_df



def get_user_taste(id_user):
     
    cursor = db.cursor()
    query = "SELECT IDfilm, note FROM userchoice WHERE IDclient = %s"
    cursor.execute(query, id_user)
    results = cursor.fetchall()
    cursor.close()
    
    ratings_df = pd.DataFrame(results, columns=['IDfilm', 'note'])

    cursor = db.cursor()
    movie_ids = ratings_df['IDfilm'].tolist()
    placeholders = ','.join(['%s'] * len(movie_ids))
    query = f"SELECT IDfilm, Name FROM film WHERE IDfilm IN ({placeholders})"
    cursor.execute(query, movie_ids)
    movie_results = cursor.fetchall()
    cursor.close()

    movie_names_df = pd.DataFrame(movie_results, columns=['IDfilm', 'Name'])
    user_ratings = pd.merge(ratings_df, movie_names_df, on='IDfilm')
    user_ratings = user_ratings.loc[:, ['Name', 'note']]
    user_ratings = user_ratings.dropna(subset=['note'])
    return user_ratings

def get_similar_movies(movie_name, rating):
    if movie_name in corrMatrix.columns:
        similar_ratings = corrMatrix[movie_name] * (rating - 5)
        similar_movies = pd.DataFrame({'Movie': similar_ratings.index, 'Similarity': similar_ratings.values})
       
        return similar_movies
    else:
        return pd.DataFrame(columns=['Movie', 'Similarity'])  

# Fonction qui enlève les dates entre les '()' --> affiche un poster pour chaque film 
def delete_dates(data):
    result = []
    for item in data:
        index = item.rfind('(')
        
        if index != -1:
            if ')' in item[index:]:
                closing_index = item[index:].find(')') + index
                item = item[:index] + item[closing_index+1:].lstrip()    
        result.append(item)
        
    
    return result
#AlgoRecommendation()

if __name__ == '__main__':
    
    app.run(debug=True)
