from PIL import Image
import os
DEMO_CLASSES=[
("Plastic Bottle","Plastic",True,True,"Plastic recycling bin","Plastic can persist for centuries if littered.","Rinse before recycling."),
("Cardboard","Paper",True,True,"Paper/cardboard recycling","Paper waste contributes to landfill volume when not recovered.","Keep dry and flatten boxes."),
("Glass Bottle","Glass",True,True,"Glass recycling center","Glass is highly recyclable but can injure handlers if broken.","Handle broken glass carefully."),
("Food Scraps","Organic",False,True,"Composting/organic bin","Organic waste in landfills can generate methane.","Compost where possible."),
("Aluminium Can","Metal",True,True,"Metal recycling bin","Recovering metals reduces mining demand.","Empty and rinse the can."),
("Old Mobile Phone","E-Waste",True,False,"Authorized e-waste center","Electronics can contain valuable and hazardous materials.","Do not place in household bins.")]
def identify_waste(image_path):
    try:
        with Image.open(image_path) as im: im.verify()
    except Exception as exc: raise ValueError("Invalid or unreadable image") from exc
    idx=sum(bytearray(os.path.basename(image_path).encode()))%len(DEMO_CLASSES)
    n,c,r,u,d,i,s=DEMO_CLASSES[idx]
    return {"name":n,"category":c,"confidence":round(.88+(idx%9)/100,2),"recyclable":r,"reusable":u,"disposal_method":d,"environmental_impact":i,"safety":s,"is_demo":True}
