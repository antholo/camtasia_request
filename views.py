# camtasia_request/views.py

from flask import Flask, render_template, request, session, flash, redirect, url_for
from flask_mail import Mail, Message
from flask_wtf.csrf import CsrfProtect
from functools import wraps
from forms import RequestForm
import requests
import os
import auth2 as d2lauth
from datetime import date

##########
# config #
##########


app = Flask(__name__)
app.config.from_pyfile('app_config.cfg')
mail = Mail(app)
app.secret_key = os.urandom(24)
CsrfProtect(app)

appContext = d2lauth.fashion_app_context(app_id=app.config['APP_ID'],
                                         app_key=app.config['APP_KEY'])
# constants for calculating semester code
BASE_YEAR = 1945
FALL = '0'
SPRING = '5'
SUMMER = '8'

JAN = 1
MAY = 5
AUG = 8
DEC = 12


############
# wrappers #
############


def login_required(test):
    @wraps(test)
    def wrap(*args, **kwargs):
        if 'userContext' in session:
            return test(*args, **kwargs)
        else:
            flash('You need to login first.')
            return redirect(url_for('login'))
    return wrap


##########
# routes #
##########


@app.route('/logout')
@login_required
def logout():
    '''
    Clears stored session information.
    '''
    session.clear()
    return redirect(app.config['REDIRECT_AFTER_LOGOUT'])


@app.route('/')
@app.route('/login')
def login():
    '''
    Checks if user context is stored in session and redirects to authorization
    handler if it is. If not, renders login template with link to D2L login and
    callback route to authorization handler.
    '''
    if 'userContext' in session:
        return redirect(url_for(app.config['AUTH_ROUTE']))
    else:
        authUrl = appContext.create_url_for_authentication(
            host=app.config['LMS_HOST'], 
            client_app_url=app.config['AUTH_CB'],
            encrypt_request=app.config['ENCRYPT_REQUESTS'])
        return render_template('login.html', authUrl=authUrl)


@app.route(app.config['AUTH_ROUTE'])
def auth_handler():
    '''
    Creates and stores user context and details.
    '''
    uc = appContext.create_user_context(
        result_uri=request.url, 
        host=app.config['LMS_HOST'],
        encrypt_requests=app.config['ENCRYPT_REQUESTS'])

    session['userContext'] = uc.get_context_properties()
    '''
    my_url = uc.create_authenticated_url(
        '/d2l/api/lp/{0}/users/whoami'.format(app.config['VER']))
    r = requests.get(my_url)
    session['firstName'] = r.json()['FirstName']
    session['lastName'] = r.json()['LastName']
    session['userId'] = r.json()['Identifier']
    '''
    userData = get_user_data(uc)
    session['firstName'] = userData['FirstName']
    session['lastName'] = userData['LastName']
    session['userId'] = userData['Identifier']
    """PRODUCTION: UNCOMMENT FOLLOWING LINE AND DELETE THE ONE AFTER THAT"""
    #session['uniqueName'] = userData['UniqueName']
    session['uniqueName'] = 'lookerb'

    code = get_semester_code()
    courseList = get_courses(uc, code)
    print("COURSE LIST", courseList)
    session['courseList'] = courseList

    return redirect(url_for('request_form'))


@app.route('/request', methods=['GET', 'POST'])
@login_required
def request_form():
    '''
    '''
    error = None
    uc = appContext.create_user_context(
        d2l_user_context_props_dict=session['userContext'])
    form = RequestForm(request.form)
    form.course.choices = get_course_choices(session['courseList'])
    print(form.course.choices)
    if request.method == 'POST':
        print("POST")
        if form.is_submitted() and form.validate_on_submit():
            print("SUBMIT")
            embed = 'no'
            if form.embed.data:
                embed = 'yes'
            download = 'no'
            if form.download.data:
                download = 'yes'
            share = 'no'
            if form.share.data:
                share = 'yes'
            training = 'no'
            if form.training.data:
                training = 'yes'

            session['requestDetails'] = {
                'courseId' : form.course.data,
                'embed' : embed,
                'download' : download,
                'share' : share,
                'training' : training,
                'location' : form.location.data,
                'courseName' : form.courseName.data,
                'comments' : form.comments.data,
                'expiration' : form.expiration.data}
            return redirect(url_for('confirm_request'))
        else:
            print("NOT SUBMITTED")
            return render_template("request.html", form=form, error=error)
    else:
        print("GET")
        return render_template("request.html", form=form, error=error)


@app.route('/confirmation')
@login_required
def confirm_request():
    submitterEmail = session['uniqueName'] + app.config['EMAIL_DOMAIN']
    msg = Message(subject='Relay account setup',
        recipients=[app.config['MAIL_DEFAULT_SENDER'],
        submitterEmail])
    msg.body = make_msg_text(session['firstName'],
        session['lastName'],
        session['requestDetails'])
    msg.html = make_msg_html(session['firstName'],
        session['lastName'],
        submitterEmail,
        session['requestDetails'])
    mail.send(msg)
    return render_template("confirmation.html")


###########
# helpers #
###########


def make_msg_text(firstName, lastName, submitterEmail, requestDetails):
    email = 'Your E-Mail Address\n\t{0}\n'.format(submitterEmail)
    name =  'Name\n\t{0} {1}\n'.format(firstName, lastName)
    embed = '{0}\n\t{1}\n'.format(form.embed.label, requestDetails['embed'])
    download = '{0}\n\t{1}\n'.format(form.download.label,
        requestDetails['download'])
    share = '{0}\n\t{1}\n'.format(form.share.label, requestDetails['share'])
    ouNumber = 'OU Number\n\t{0}\n'.format(requestDetails['courseId'])
    location = '{0}\n\t{1}'.format(form.location.label,
        requestDetails['location'])
    courseName = '{0}\n\t{1}\n'.format(form.courseName.label,
        requestDetails['courseName'])
    expiration = '{0}\n\t{1}\n'.format(form.expiration.label,
        requestDetails['expiration'])
    training = '{0}\n\t{1}\n'.format(form.training.label,
        requestDetails['training'])
    comments = '{0}\n\t{1}\n'.format(form.comments.label,
        requestDetails['comments'])
    return email, name, embed, download, share, ouNumber, location, \
        courseName, expiration, training, comments


def make_msg_html(firstName, lastName, submitterEmail, requestDetails):
    email = '<dl><dt>Your E-Mail Address</dt><dd><a href=3D"mailto:{0}' + \
         ' target=3D"_blank">{0}</a></dd>'.format(submitterEmail)
    name = '<dt>Name</dt><dd>{0} {1}</dd>'.format(firstName, lastName)
    embed = '<dt>{0}</dt><dd>{1}</dd>'.format(form.embed.label,
        requestDetails['embed'])
    download = '<dt>{0}</dt><dd>{1}</dd>'.format(form.download.label,
        requestDetails['download'])
    share = '<dt>{0}<dt><dd>{1}</dd>'.format(form.share.label,
        requestDetails['share'])
    ouNumber = '<dt>OU Number</dt><dd>{0}</dd>'.format(requestDetails['courseId'])
    location = '<dt>{0}</dt><dd>{1}</dd>'.format(form.location.label,
        requestDetails['location'])
    courseName = '<dt>{0}</dt><dd>{1}</dd>'.format(form.courseName.label,
        requestDetails['courseName'])
    expiration = '<dt>{0}</dt><dd>{1}</dd>'.format(form.expiration.label,
        requestDetails['expiration'])
    training = '<dt>{0}</dt><dd>{1}</dd>'.format(form.training.label,
        requestDetails['training'])
    comments = '<dt>{0}</dt><dd>{1}</dd>'.format(form.comments.label,
        requestDetails['comments'])
    return email, name, embed, download, share, ouNumber, location, \
        courseName, expiration, training, comments


def get_user_data(uc):
    my_url = uc.create_authenticated_url(
        '/d2l/api/lp/{0}/users/whoami'.format(app.config['VER']))
    return requests.get(my_url).json()


def get_course_choices(courseList):
    linkPrefix = "<a target=\"_blank\" href='http://" + \
        app.config['LMS_HOST'] + \
        "/d2l/lp/manageCourses/course_offering_info_viewedit.d2l?ou="
    choices = [(course['courseId'],
        course['name'] +
        ", " +
        course['parsed'] +
        linkPrefix +
        str(course['courseId']) +
        "'>D2L Page</a>") for course in courseList]
    return choices


def get_semester_code():
    year = date.today().year
    month = date.today().month
    if month >= 8 and month <= 12:
        semester = FALL
    elif month >= 1 and month <= 5:
        semester = SPRING
    else: # month is between
        semester = SUMMER
    code = str(year - BASE_YEAR) + semester
    while len(code) < 4:
        code = '0' + code
    return code


def get_courses(uc, code):
    '''
    Creates dictionary of lists of courses keyed by semester code and stores 
    it in session for easy access post-creation.
    '''
    myUrl = uc.create_authenticated_url(
        '/d2l/api/lp/{0}/enrollments/myenrollments/'.format(app.config['VER']))
    kwargs = {'params': {}}
    kwargs['params'].update({'orgUnitTypeId': app.config['ORG_UNIT_TYPE_ID']})
    r = requests.get(myUrl, **kwargs)
    courseList = []
    end = False
    while end == False:
        for course in r.json()['Items']:
            semCode = str(course['OrgUnit']['Code'][6:10])
            print("SEMCODE", semCode, "CODE", code)
            if semCode == code:
                courseList.append({u'courseId': int(courseId),
                    u'name': name,
                    u'code': code,
                    u'parsed': parse_code(code)})
            if r.json()['PagingInfo']['HasMoreItems'] == True:
                kwargs['params']['bookmark'] = r.json()['PagingInfo']['Bookmark']
                r = requests.get(myUrl, **kwargs)
            else:
                end = True
    return courseList


def parse_code(code):
    '''
    Breaks up code into more readable version to present to user.
    '''
    parsed = code.split("_")
    return parsed[3] + " " + parsed[4] + " " + parsed[5]

if __name__ == '__main__':
    app.run(debug=True)