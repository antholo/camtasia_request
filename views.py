# camtasia_request/views.py

from flask import Flask, render_template, request, session, flash, redirect, url_for
from flask_mail import Mail, Message
from flask_wtf.csrf import CsrfProtect
from functools import wraps
from form import SelectSemesterForm, SelectCoursesForm, AdditionalCourseForm
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

    my_url = uc.create_authenticated_url(
        '/d2l/api/lp/{0}/users/whoami'.format(app.config['VER']))
    r = requests.get(my_url)

    session['firstName'] = r.json()['FirstName']
    session['lastName'] = r.json()['LastName']
    session['userId'] = r.json()['Identifier']

    """PRODUCTION: UNCOMMENT FOLLOWING LINE AND DELETE THE ONE AFTER THAT"""
    #session['uniqueName'] = r.json()['UniqueName']
    session['uniqueName'] = 'lookerb'

    code = get_semester_code()
    courseList = get_courses(uc, code)
    session['courseList'] = courseList

    return redirect(url_for('request'))


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
    if request.method == 'POST':
        if form.is_submitted() and form.validate_on_submit():
            session['requestDetails'] = {
                'courseId' : form.course.data
                'embed' : form.embed.data
                'download' : form.download.data
                'share' : form.share.data
                'training' : form.training.data
                'location' : form.location.data
                'courseName' : form.courseName.data
                'comments' : form.comments.data
                'expiration' : form.expiration.data}
            return redirect(url_for('confirm_request'))

    else:
        render_template("request.html", form=form, error=error)


@app.route('/confirmation')
@login_required
def confirm_request():
    msg = Message(subject='Course Combine Confirmation',
        recipients=[app.config['MAIL_DEFAULT_SENDER'],
        session['uniqueName'] + app.config['EMAIL_DOMAIN']])
    msg.body = make_msg_text(session['firstName'],
        session['lastName'],
        session['requestDetails'])



###########
# helpers #
###########


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
    while len(semesterCode) < 4:
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
            if semCode == code:
                courseList.append({{u'courseId': int(courseId),
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