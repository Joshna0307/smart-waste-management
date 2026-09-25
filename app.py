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
class WasteReport(db.Model):
 __tablename__="waste_reports"
 id=db.Column(db.Integer,primary_key=True);user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False);report_id=db.Column(db.String(30),unique=True);issue_type=db.Column(db.String(80));location=db.Column(db.String(255));description=db.Column(db.Text);severity=db.Column(db.String(30),default="Medium");image_path=db.Column(db.String(255));status=db.Column(db.String(30),default="Open");created_at=db.Column(db.DateTime,default=datetime.datetime.utcnow)
class Notification(db.Model):
 id=db.Column(db.Integer,primary_key=True);user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False);title=db.Column(db.String(160));message=db.Column(db.Text);category=db.Column(db.String(50));is_read=db.Column(db.Boolean,default=False);created_at=db.Column(db.DateTime,default=datetime.datetime.utcnow)
class DisposalCenter(db.Model):
 id=db.Column(db.Integer,primary_key=True);name=db.Column(db.String(160));center_type=db.Column(db.String(80));address=db.Column(db.Text);latitude=db.Column(db.Float);longitude=db.Column(db.Float);opening_hours=db.Column(db.String(120));accepted_waste=db.Column(db.String(255));phone=db.Column(db.String(30))

class SmartBin(db.Model):
 __tablename__="smart_bins"
 id=db.Column(db.Integer,primary_key=True);name=db.Column(db.String(120),nullable=False);location=db.Column(db.String(255));latitude=db.Column(db.Float);longitude=db.Column(db.Float);fill_level=db.Column(db.Float,default=0);weight=db.Column(db.Float,default=0);battery=db.Column(db.Float,default=100);status=db.Column(db.String(30),default="Online");updated_at=db.Column(db.DateTime,default=datetime.datetime.utcnow)
class MarketplaceItem(db.Model):
 __tablename__="marketplace_items"
 id=db.Column(db.Integer,primary_key=True);user_id=db.Column(db.Integer,db.ForeignKey("users.id"),nullable=False);title=db.Column(db.String(160),nullable=False);category=db.Column(db.String(80));condition=db.Column(db.String(50));description=db.Column(db.Text);location=db.Column(db.String(180));status=db.Column(db.String(30),default="Available");created_at=db.Column(db.DateTime,default=datetime.datetime.utcnow)
class ContactMessage(db.Model):
 id=db.Column(db.Integer,primary_key=True);name=db.Column(db.String(120));email=db.Column(db.String(160));phone=db.Column(db.String(30));subject=db.Column(db.String(160));message=db.Column(db.Text);created_at=db.Column(db.DateTime,default=datetime.datetime.utcnow)
class DatabaseResetMarker(db.Model):
 __tablename__="database_reset_marker"
 id=db.Column(db.Integer,primary_key=True);completed_at=db.Column(db.DateTime,default=datetime.datetime.utcnow,nullable=False)
WASTE_INFO={"Organic":("Food scraps, leaves and biodegradable material","Compost or use an organic bin"),"Plastic":("Bottles, containers and packaging","Clean, dry and send accepted plastics to recycling"),"Paper":("Paper, newspapers and cardboard","Keep dry and recycle"),"Glass":("Bottles and jars","Use glass recycling where accepted"),"Metal":("Cans and metal containers","Rinse and recycle accepted metals"),"E-Waste":("Phones, computers and electronics","Use authorized e-waste collection"),"Hazardous":("Paints, chemicals and certain batteries","Use specialized hazardous-waste collection"),"Biomedical":("Sharps and contaminated clinical waste","Use authorized biomedical channels")}
CENTERS=[]
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
@app.route("/collect-report",methods=["GET","POST"])
@login_required
def collect_report():
 if request.method=="POST":
  action=request.form.get("action","").strip()
  if action=="collect":
   rid=f"SWM-{datetime.datetime.now().year}-{CollectionRequest.query.count()+1:04d}"
   c=CollectionRequest(user_id=session["user_id"],request_id=rid,waste_type=request.form.get("waste_type"),quantity=request.form.get("quantity"),address=request.form.get("address"),landmark=request.form.get("landmark"),preferred_date=request.form.get("preferred_date"),preferred_time=request.form.get("preferred_time"),phone=request.form.get("phone"),notes=request.form.get("notes"))
   db.session.add(c);db.session.add(Notification(user_id=session["user_id"],title="Collection request created",message=f"Request {rid} is pending.",category="Collection"));db.session.commit();flash(f"Collection request {rid} created.","success");return redirect(url_for("collect_report"))
  if action=="report":
   f=request.files.get("report_image");image_path=None
   if f and f.filename:
    ext=f.filename.rsplit(".",1)[-1].lower() if "." in f.filename else ""
    if ext in app.config["ALLOWED_EXTENSIONS"]:
     fn=secure_filename(uuid.uuid4().hex+"."+ext);f.save(os.path.join(app.config["UPLOAD_FOLDER"],fn));image_path="uploads/"+fn
   rid=f"RPT-{datetime.datetime.now().year}-{WasteReport.query.count()+1:04d}"
   r=WasteReport(user_id=session["user_id"],report_id=rid,issue_type=request.form.get("issue_type"),location=request.form.get("report_location"),description=request.form.get("report_description"),severity=request.form.get("severity","Medium"),image_path=image_path)
   db.session.add(r);db.session.add(Notification(user_id=session["user_id"],title="Waste report submitted",message=f"Report {rid} was submitted for review.",category="Report"));db.session.commit();flash(f"Waste report {rid} submitted successfully.","success");return redirect(url_for("collect_report"))
 return render_template("collect_report.html",requests=CollectionRequest.query.filter_by(user_id=session["user_id"]).order_by(CollectionRequest.created_at.desc()).all(),reports=WasteReport.query.filter_by(user_id=session["user_id"]).order_by(WasteReport.created_at.desc()).all())

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

IMPACT_FACTORS={"Plastic":0.8,"Paper":1.2,"Glass":0.3,"Metal":2.0,"Organic":0.2,"E-Waste":1.5,"Textile":1.1,"Hazardous":0.4,"Biomedical":0.1}

def _impact_summary(uid):
 records=WasteRecord.query.filter_by(user_id=uid).all()
 totals={}
 for r in records: totals[r.waste_category]=totals.get(r.waste_category,0)+1
 diverted=sum(totals.get(k,0) for k in ("Plastic","Paper","Glass","Metal","E-Waste","Textile"))
 co2=round(sum(totals.get(k,0)*v for k,v in IMPACT_FACTORS.items()),2)
 return {"records":len(records),"diverted_items":diverted,"co2_saved":co2,"landfill_avoided":round(diverted*0.35,2),"categories":totals}

def _forecast(uid):
 now=datetime.datetime.utcnow();start=now-datetime.timedelta(days=7)
 rows=WasteRecord.query.filter(WasteRecord.user_id==uid,WasteRecord.created_at>=start).all()
 weekly=len(rows);daily=weekly/7 if weekly else 0
 return {"last_7_days":weekly,"daily_average":round(daily,2),"next_30_days":round(daily*30,1),"trend":"Growing" if daily>0 else "No recent activity"}

@app.route("/eco-hub")
@login_required
def eco_hub():
 uid=session["user_id"];impact=_impact_summary(uid);forecast=_forecast(uid)
 bins=SmartBin.query.order_by(SmartBin.fill_level.desc()).limit(6).all()
 items=MarketplaceItem.query.filter_by(status="Available").order_by(MarketplaceItem.created_at.desc()).limit(4).all()
 return render_template("eco_hub.html",impact=impact,forecast=forecast,bins=bins,items=items)

@app.route("/smart-bins")
@login_required
def smart_bins():
 return render_template("smart_bins.html",bins=SmartBin.query.order_by(SmartBin.fill_level.desc()).all())

@app.get("/api/smart-bins")
def api_smart_bins():
 return jsonify([{"id":b.id,"name":b.name,"location":b.location,"lat":b.latitude,"lng":b.longitude,"fill":b.fill_level,"weight":b.weight,"battery":b.battery,"status":b.status} for b in SmartBin.query.all()])

@app.route("/impact")
@login_required
def impact():
 return render_template("impact.html",impact=_impact_summary(session["user_id"]),forecast=_forecast(session["user_id"]))

@app.route("/eco-simulator",methods=["GET","POST"])
@login_required
def eco_simulator():
 reduction=float(request.form.get("reduction",20) or 20) if request.method=="POST" else 20
 reduction=max(0,min(100,reduction));f=_forecast(session["user_id"]);baseline=f["next_30_days"];projected=round(baseline*(1-reduction/100),1)
 return render_template("eco_simulator.html",reduction=reduction,baseline=baseline,projected=projected,avoided=round(baseline-projected,1))

@app.route("/marketplace",methods=["GET","POST"])
@login_required
def marketplace():
 if request.method=="POST":
  title=request.form.get("title","").strip()
  if title:
   db.session.add(MarketplaceItem(user_id=session["user_id"],title=title,category=request.form.get("category"),condition=request.form.get("condition"),description=request.form.get("description"),location=request.form.get("location")));db.session.commit();flash("Reusable item listed successfully.","success");return redirect(url_for("marketplace"))
 return render_template("marketplace.html",items=MarketplaceItem.query.filter_by(status="Available").order_by(MarketplaceItem.created_at.desc()).all())

@app.route("/admin")
@login_required
def admin():
 admin_email=os.environ.get("ADMIN_EMAIL","").strip().lower()
 u=User.query.get(session["user_id"])
 if not admin_email or not u or u.email.lower()!=admin_email: return render_template("error.html",code=403,message="Admin access is not enabled for this account."),403
 return render_template("admin.html",users=User.query.count(),records=WasteRecord.query.count(),requests=CollectionRequest.query.count(),reports=WasteReport.query.count(),messages=ContactMessage.query.count(),bins=SmartBin.query.count(),items=MarketplaceItem.query.count(),impact=_impact_summary(session["user_id"]))

@app.get("/api/eco-forecast")
@login_required
def api_eco_forecast(): return jsonify(_forecast(session["user_id"]))

@app.errorhandler(404)
def not_found(e):return render_template("error.html",code=404,message="Page not found"),404
@app.errorhandler(500)
def server_error(e):db.session.rollback();return render_template("error.html",code=500,message="Something went wrong"),500
with app.app_context():
 db.create_all()
 # One-time clean start for the current deployment. The marker prevents
 # later Vercel cold starts from deleting newly created user data.
 reset_database = os.environ.get("RESET_DATABASE_ON_STARTUP", "true").strip().lower() == "true"
 if reset_database and DatabaseResetMarker.query.count() == 0:
  db.drop_all()
  db.create_all()
  db.session.add(DatabaseResetMarker())
  db.session.commit()
if __name__=="__main__":app.run(debug=True)
