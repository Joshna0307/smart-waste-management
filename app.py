import os,uuid,datetime
from functools import wraps
from flask import Flask,render_template,request,redirect,url_for,session,flash,jsonify
from werkzeug.security import generate_password_hash,check_password_hash
from werkzeug.utils import secure_filename
from config import Config
from models import db
from services.ai_classifier import identify_waste
from services.chatbot import reply
app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
# Vercel entry point: expose the Flask instance at module scope.
application = app
if os.path.abspath(app.config["UPLOAD_FOLDER"]).startswith("/tmp"):
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
class User(db.Model):
 __tablename__="users"
 id=db.Column(db.Integer,primary_key=True);name=db.Column(db.String(120),nullable=False);email=db.Column(db.String(160),unique=True,nullable=False);phone=db.Column(db.String(30));password_hash=db.Column(db.String(255),nullable=False);profile_image=db.Column(db.String(255));environmental_points=db.Column(db.Integer,default=0);created_at=db.Column(db.DateTime,default=datetime.datetime.utcnow)
class WasteRecord(db.Model):
 id=db.Column(db.Integer,primary_key=True);user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False);waste_name=db.Column(db.String(120));waste_category=db.Column(db.String(60));confidence=db.Column(db.Float);recyclable=db.Column(db.Boolean);reusable=db.Column(db.Boolean);disposal_method=db.Column(db.String(255));image_path=db.Column(db.String(255));created_at=db.Column(db.DateTime,default=datetime.datetime.utcnow)
class CollectionRequest(db.Model):
 id=db.Column(db.Integer,primary_key=True);user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False);request_id=db.Column(db.String(30),unique=True);waste_type=db.Column(db.String(60));quantity=db.Column(db.String(60));address=db.Column(db.Text);landmark=db.Column(db.String(160));preferred_date=db.Column(db.String(30));preferred_time=db.Column(db.String(30));phone=db.Column(db.String(30));notes=db.Column(db.Text);status=db.Column(db.String(30),default="Pending");created_at=db.Column(db.DateTime,default=datetime.datetime.utcnow)
class Notification(db.Model):
 id=db.Column(db.Integer,primary_key=True);user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False);title=db.Column(db.String(160));message=db.Column(db.Text);category=db.Column(db.String(50));is_read=db.Column(db.Boolean,default=False);created_at=db.Column(db.DateTime,default=datetime.datetime.utcnow)
class DisposalCenter(db.Model):
 id=db.Column(db.Integer,primary_key=True);name=db.Column(db.String(160));center_type=db.Column(db.String(80));address=db.Column(db.Text);latitude=db.Column(db.Float);longitude=db.Column(db.Float);opening_hours=db.Column(db.String(120));accepted_waste=db.Column(db.String(255));phone=db.Column(db.String(30))
class ContactMessage(db.Model):
 id=db.Column(db.Integer,primary_key=True);name=db.Column(db.String(120));email=db.Column(db.String(160));phone=db.Column(db.String(30));subject=db.Column(db.String(160));message=db.Column(db.Text);created_at=db.Column(db.DateTime,default=datetime.datetime.utcnow)
WASTE_INFO={"Organic":("Food scraps, leaves and biodegradable material","Compost or use an organic bin"),"Plastic":("Bottles, containers and packaging","Clean, dry and send accepted plastics to recycling"),"Paper":("Paper, newspapers and cardboard","Keep dry and recycle"),"Glass":("Bottles and jars","Use glass recycling where accepted"),"Metal":("Cans and metal containers","Rinse and recycle accepted metals"),"E-Waste":("Phones, computers and electronics","Use authorized e-waste collection"),"Hazardous":("Paints, chemicals and certain batteries","Use specialized hazardous-waste collection"),"Biomedical":("Sharps and contaminated clinical waste","Use authorized biomedical channels")}
CENTERS=[("GreenCycle Recycling","Recycling Center","Main Road",10.76,78.69,"09:00-18:00","Plastic, Paper, Glass, Metal","9000000001"),("EcoDrop E-Waste","E-Waste Center","Tech Park Road",10.77,78.70,"10:00-17:00","E-Waste","9000000002"),("Compost Hub","Composting Center","Market Road",10.75,78.68,"07:00-16:00","Organic","9000000003"),("Dry Waste Point","Waste Collection Point","Bus Stand Road",10.765,78.685,"08:00-20:00","Plastic, Paper, Metal, Glass","9000000004")]
def login_required(fn):
 @wraps(fn)
 def wrapper(*a,**k):
  if "user_id" not in session: flash("Please log in to continue.","warning");return redirect(url_for("login"))
  return fn(*a,**k)
 return wrapper
@app.context_processor
def globals():
 u=User.query.get(session.get("user_id")) if session.get("user_id") else None
 unread=Notification.query.filter_by(user_id=session.get("user_id"),is_read=False).count() if u else 0
 return {"current_user":u,"unread_count":unread}
@app.route("/")
def index(): return render_template("index.html")
@app.route("/signup",methods=["GET","POST"])
def signup():
 if request.method=="POST":
  name=request.form.get("name","").strip();email=request.form.get("email","").strip().lower();p=request.form.get("password","");c=request.form.get("confirm_password","")
  if not name or "@" not in email or len(p)<6 or p!=c: flash("Enter valid details and matching password (6+ characters).","danger")
  elif User.query.filter_by(email=email).first(): flash("Email already registered.","danger")
  else: db.session.add(User(name=name,email=email,phone=request.form.get("phone"),password_hash=generate_password_hash(p)));db.session.commit();flash("Account created. Please log in.","success");return redirect(url_for("login"))
 return render_template("signup.html")
@app.route("/login",methods=["GET","POST"])
def login():
 if request.method=="POST":
  u=User.query.filter_by(email=request.form.get("email","").strip().lower()).first()
  if u and check_password_hash(u.password_hash,request.form.get("password","")):session["user_id"]=u.id;return redirect(url_for("dashboard"))
  flash("Incorrect email or password.","danger")
 return render_template("login.html")
@app.route("/logout")
def logout():session.clear();flash("Logged out successfully.","success");return redirect(url_for("index"))
@app.route("/dashboard")
@login_required
def dashboard():
 uid=session["user_id"];records=WasteRecord.query.filter_by(user_id=uid).order_by(WasteRecord.created_at.desc()).all();reqs=CollectionRequest.query.filter_by(user_id=uid).all();counts={c:sum(r.waste_category==c for r in records) for c in ["Organic","Plastic","Paper","Glass","Metal","E-Waste"]};return render_template("dashboard.html",records=records[:6],reqs=reqs,counts=counts)
@app.route("/waste-types")
def waste_types():return render_template("waste_types.html",waste_info=WASTE_INFO)
@app.route("/pollution")
def pollution():return render_template("pollution.html")
@app.route("/ai-identifier",methods=["GET","POST"])
@login_required
def ai_identifier():
 result=None
 if request.method=="POST":
  f=request.files.get("image");ext=f.filename.rsplit(".",1)[-1].lower() if f and "." in f.filename else ""
  if not f or not f.filename:flash("Choose an image.","danger")
  elif ext not in app.config["ALLOWED_EXTENSIONS"]:flash("Allowed images: PNG, JPG, JPEG, WEBP.","danger")
  else:
   fn=secure_filename(uuid.uuid4().hex+"."+ext);path=os.path.join(app.config["UPLOAD_FOLDER"],fn);f.save(path);result=identify_waste(path);db.session.add(WasteRecord(user_id=session["user_id"],waste_name=result["name"],waste_category=result["category"],confidence=result["confidence"],recyclable=result["recyclable"],reusable=result["reusable"],disposal_method=result["disposal_method"],image_path="uploads/"+fn));u=User.query.get(session["user_id"]);u.environmental_points+=10;db.session.add(Notification(user_id=u.id,title="Waste identified",message=result["name"]+" was identified using the local demo classifier.",category="AI"));db.session.commit()
 return render_template("ai_identifier.html",result=result)
@app.route("/classification")
@login_required
def classification():return render_template("classification.html",waste_info=WASTE_INFO)
@app.route("/recycle")
@login_required
def recycle():return render_template("recycle.html")
@app.route("/collection",methods=["GET","POST"])
@login_required
def collection():
 if request.method=="POST":
  rid=f"SWM-{datetime.datetime.now().year}-{CollectionRequest.query.count()+1:04d}";c=CollectionRequest(user_id=session["user_id"],request_id=rid,waste_type=request.form.get("waste_type"),quantity=request.form.get("quantity"),address=request.form.get("address"),landmark=request.form.get("landmark"),preferred_date=request.form.get("preferred_date"),preferred_time=request.form.get("preferred_time"),phone=request.form.get("phone"),notes=request.form.get("notes"));db.session.add(c);db.session.add(Notification(user_id=session["user_id"],title="Collection request created",message=f"Request {rid} is pending.",category="Collection"));db.session.commit();flash(f"Collection request {rid} created.","success");return redirect(url_for("collection"))
 return render_template("collection.html",requests=CollectionRequest.query.filter_by(user_id=session["user_id"]).order_by(CollectionRequest.created_at.desc()).all())
@app.route("/disposal-map")
def disposal_map():return render_template("disposal_map.html",centers=DisposalCenter.query.all())
@app.route("/notifications")
@login_required
def notifications():return render_template("notifications.html",notifications=Notification.query.filter_by(user_id=session["user_id"]).order_by(Notification.created_at.desc()).all())
@app.route("/notifications/read/<int:nid>",methods=["POST"])
@login_required
def notification_read(nid):
 n=Notification.query.filter_by(id=nid,user_id=session["user_id"]).first_or_404();n.is_read=True;db.session.commit();return redirect(url_for("notifications"))
@app.route("/profile",methods=["GET","POST"])
@login_required
def profile():
 u=User.query.get(session["user_id"])
 if request.method=="POST":
  u.name=request.form.get("name",u.name).strip();u.phone=request.form.get("phone",u.phone);f=request.files.get("profile_image")
  if f and f.filename:
   ext=f.filename.rsplit(".",1)[-1].lower()
   if ext in app.config["ALLOWED_EXTENSIONS"]:fn=secure_filename(uuid.uuid4().hex+"."+ext);f.save(os.path.join(app.config["UPLOAD_FOLDER"],fn));u.profile_image="uploads/"+fn
  db.session.commit();flash("Profile updated.","success")
 return render_template("profile.html",user=u)
@app.route("/contact",methods=["GET","POST"])
def contact():
 if request.method=="POST":db.session.add(ContactMessage(name=request.form.get("name"),email=request.form.get("email"),phone=request.form.get("phone"),subject=request.form.get("subject"),message=request.form.get("message")));db.session.commit();flash("Message sent successfully.","success");return redirect(url_for("contact"))
 return render_template("contact.html")
@app.post("/api/chat")
def api_chat():return jsonify({"reply":reply((request.json or {}).get("message",""))})
@app.get("/api/disposal-centers")
def api_centers():return jsonify([{"name":c.name,"type":c.center_type,"address":c.address,"lat":c.latitude,"lng":c.longitude,"hours":c.opening_hours,"accepted":c.accepted_waste,"phone":c.phone} for c in DisposalCenter.query.all()])
@app.get("/api/waste-statistics")
@login_required
def api_stats():
 rows=WasteRecord.query.filter_by(user_id=session["user_id"]).all();return jsonify({c:sum(r.waste_category==c for r in rows) for c in WASTE_INFO})
@app.post("/api/notifications/read")
@login_required
def api_read():Notification.query.filter_by(user_id=session["user_id"]).update({"is_read":True});db.session.commit();return jsonify({"ok":True})
@app.errorhandler(404)
def not_found(e):return render_template("error.html",code=404,message="Page not found"),404
@app.errorhandler(500)
def server_error(e):db.session.rollback();return render_template("error.html",code=500,message="Something went wrong"),500
with app.app_context():
 db.create_all()
 if DisposalCenter.query.count()==0:
  for n,t,a,lat,lng,h,w,p in CENTERS:db.session.add(DisposalCenter(name=n,center_type=t,address=a,latitude=lat,longitude=lng,opening_hours=h,accepted_waste=w,phone=p))
  db.session.commit()
if __name__=="__main__":app.run(debug=True)
