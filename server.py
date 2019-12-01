from flask import Flask,render_template,request;        # used for actual flask object, android user's request object and rendering an already exisiting html page
from flask_socketio import SocketIO,send,emit;            # used to create the socket server object and use the emit and send functionalities
import MySQLdb;                                    # used for connecting python to local SQL database
import json;                                            # used for encoding huge data into a json encoded object
import os;                                                # used to call OS commands
import sys;                               
#import base64;
import time;

app=Flask(__name__);

connection = MySQLdb.connect(host="localhost",
                           user = "root",
                           passwd = "beam",
                           db = "beam_postinc");
myCursor=connection.cursor();

socketIO_Object=SocketIO(app);

#  ******************************   ADMIN PANEL PAGE    *******************************
@app.route('/')
def index():
    print("Index Page Visited!!");
    print("Received IP Address :"+request.remote_addr);
    return render_template("./index1.html");

# ******************************* Connection to Raspberry PI JS Clients and communicating their statuses
@socketIO_Object.on("connect")
def handleNewConnected():
    print("Connected !!!!!!!!!! :"+request.remote_addr);

@socketIO_Object.on("fromRaspPI_setConnectedFlag")
def handleAPI(id):
    print ("Projector "+str(id)+" is connected !!");
    myCursor.execute("""UPDATE projectors set connected_flag=true where projector_id=%s;""",(id));
    connection.commit();

# ****************************** New Android User Registration
@app.route("/fromAndroidRegister",methods=["post"])
def register():
    print("Registering ......");
    mobile=request.form["mobile"];
    password=request.form["password"];
    name=request.form["name"];

    try:
        myCursor.execute( """INSERT INTO users VALUES(%s,%s,%s,%s);""",(mobile,password,name,0));
        connection.commit();
        print ("Registered Sucessfully!!!");
        return "true";
    except Exception as e:
        print e;
        return "false";

# ****************************** Existing Android User Login
@app.route("/fromAndroidLogin",methods=["post"])
def login():
    print("Logging ......");
    mobile=request.form["mobile"];
    password=request.form["password"];

    payload=[];
    content={};

    try:
        myCursor.execute( """select * from users where mobile=%s and password=%s limit 1;""",(mobile,password));
        if(myCursor.rowcount>0):
            row=myCursor.fetchone();
            count_projectors=row[5];
            user_type=row[3];
            name=row[2];
            #content={"User_Name":name};
            #payload.append(content);
            payload=[];
            content={};
            projector_data=[];
            print "No of Projectors ="+str(count_projectors);
            if(count_projectors==0):
                print "Zero Projectors!";
                #content={"User_name":name,"Proj_Data":payload,"Type":user_type};
                #return json.dumps(content);
                myCursor.execute("""select count(*) from campaigns where user_mobile=%s;""",(mobile));
                row=myCursor.fetchone();
                total_campaigns=row[0];
                myCursor.execute("""select count(*) from images where user_mobile=%s;""",(mobile));
                row=myCursor.fetchone();
                total_images=row[0];
                #myCursor.execute("""select count(*) from videos where user_mobile=%s;""",(mobile));
                #row=myCursor.fetchone();
                total_videos=0;

                content={"User_name":name,"Proj_Data":payload,"total_campaigns":total_campaigns,"total_images":total_images,"total_videos":total_videos,"Type":user_type};
                return json.dumps(content);
            else:
                print "after payload init";
                if(user_type=="O"):
                    myCursor.execute("select * from projectors where owner_mobile='"+str(mobile)+"' limit "+str(count_projectors)+";");
               
                else:
                    myCursor.execute("select * from projectors where client_mobile='"+str(mobile)+"' limit "+str(count_projectors)+";");
               
                print("after query");
                resultSet=myCursor.fetchall();
                for row in resultSet:
                    myCursor.execute("""select campaign_name from campaigns where campaign_id=%s""",(row[5]));
                    result2=myCursor.fetchone();
                    camp_name=result2[0];
                    content={"Projector_ID":row[0],"Projector_Name":row[1],"Flag":row[4],"Campaign_ID":row[5],"Campaign_Name":camp_name};
                    payload.append(content);
                    content={};
                print json.dumps(payload);
                myCursor.execute("""select count(*) from campaigns where user_mobile=%s;""",(mobile));
                row=myCursor.fetchone();
                total_campaigns=row[0];
                myCursor.execute("""select count(*) from images where user_mobile=%s;""",(mobile));
                row=myCursor.fetchone();
                total_images=row[0];
                #myCursor.execute("""select count(*) from videos where user_mobile=%s;""",(mobile));
                #row=myCursor.fetchone();
                total_videos=0;

                content={"User_name":name,"Proj_Data":payload,"total_campaigns":total_campaigns,"total_images":total_images,"total_videos":total_videos,"Type":user_type};
                #return json.dumps(payload);
                #return '{"User_name": "My Name is Khan!", "Proj_Data": [{"Projector_ID": "1", "Projector_Name": "mrunalprojector1", "Campaign_ID": 0, "Flag_Connected": "666"}, {"Projector_ID": "2", "Projector_Name": "mrunalproj2", "Campaign_ID": 0, "Flag_Connected": "666"}]}';
                return json.dumps(content);
            print ("Login Sucessfully!!!");
        else:
            return "false";
       
    except Exception as e:
        print e;
        return "false";

# *********************************** Get History
@app.route("/history",methods=["POST"])
def retHistory():
    try:
        print("Gathering History !!")
        mobile=request.form["mobile"];
        myCursor.execute("""select * from history where projector_id in (select projector_id from projectors where user_mobile=%s) order by time asc;
""",(mobile));
        resultSet=myCursor.fetchall();
        history_count=myCursor.rowcount();
        payload=[];
        content={};
        for row in resultSet:
            content={"time":row[0],"projector_id":row[1],"campaign_id":row[2]};
            payload.append(content);
        content={"history":payload};
        return json.dumps(content);

    except Exception as e:
        print str(e);
        return "false";
# *********************************** Adding a new Campaign
@app.route("/addNewCampaign",methods=["POST"])
def createNewCampaignAdd():
    try:
        campaign_name=request.form["name"];
        mobile=request.form["mobile"];
        delay=request.form["delay"];
        encodedImage=request.form["image"];

        myCursor.execute( "select MAX(campaign_id) from campaigns");
        if(myCursor.rowcount>0):
            i=0;
            resultSet=myCursor.fetchone();
            new_campaign_id=resultSet[0];
            new_campaign_id=int(new_campaign_id);

            #print(type(new_campaign_id));
            #print "New Campaign ID "+str(new_campaign_id)+".";
            new_campaign_id=new_campaign_id+1;
            print("B4 insert into camp");
            myCursor.execute("""INSERT INTO campaigns values(%s,%s,%s,%s,%s,%s);""",(new_campaign_id,0,0,0,mobile,campaign_name));
            myCursor.execute("""UPDATE users set no_of_campaigns=no_of_campaigns+1 where mobile=%s""",(mobile));
            print("After insert into camp");
            #print ("NEW = :"+str(new_campaign_id));

            os.makedirs("PostINC_Camps/"+str(new_campaign_id));

            myCursor.execute("select MAX(image_id) from images");
            resultSet=myCursor.fetchone();
            new_image_id=int(resultSet[0]);
            new_image_id=new_image_id+1;
           
            with open("PostINC_Camps/"+str(new_campaign_id)+"/"+str(new_image_id)+".jpeg","wb") as file:
                file.write(encodedImage.decode('base64'));
           
            print("Image downloaded!!");
           
            myCursor.execute("""INSERT into images values(%s,%s,%s,%s,%s)""",(new_image_id,new_campaign_id,"PostINC_Camps/"+str(new_campaign_id)+"/"+str(new_image_id)+".jpeg",delay,mobile));
            myCursor.execute("""UPDATE campaigns set count_images=count_images+1 where campaign_id=%s;""",(new_campaign_id));

            print("Image Counts Incremented in Campaign Id "+str(new_campaign_id));
            #count_projectors=request.form["count_projectors"];
            #count_projectors=int(count_projectors);
           
            #print("Extracted projectors count");
            #for i in range(0,count_projectors):   
                #projector_name=request.form["projector"+str(i)];
                #myCursor.execute("""UPDATE projectors set current_campaign=%s where projector_id=%s""",(new_campaign_id,projector_name));
                           
                #content={};
                #content={"campaign_id":new_campaign_id,"Image":encodedImage};
                            
                            
                #socketIO_Object.emit(projector_name+"_img",json.dumps(content));
                #print("Emitting firt img toproj "+str(i));
            #socketIO_Object.emit("Forward_From_Android",image_string);   
            #print("Projector Name "+projector_name);
            connection.commit();

           
            #socketIO_Object.emit("1_imad",image_string);
           
            print("All changes commited!");
            return str(new_campaign_id);       

    except Exception as e:
        print "Exception "+str(e);

# *********************************** Receive Images
@app.route("/addImagesToCampaign",methods=["POST"])
def addIntoExisitingCampaign():
    try:
        mobile=request.form["mobile"];
        delay=request.form["delay"];
        current_campaign=request.form["campaign_id"];
        encodedImage=request.form["image"];
        sequence=request.form["sequence"];

        print ("Inside Exisiting Camp!");
       
        print("Exisiting Camp :"+str(current_campaign));
       
        print("Sequence :"+str(sequence));

       

        print("Encoded Received !!");
        myCursor.execute("select MAX(image_id) from images");
        resultSet=myCursor.fetchone();
        new_image_id=int(resultSet[0]);
        new_image_id=new_image_id+1;

        print ("New Image ID for Seq :"+str(sequence)+" is "+str(new_image_id));

        with open("PostINC_Camps/"+str(current_campaign)+"/"+str(new_image_id)+".jpeg","wb") as file:
            file.write(encodedImage.decode('base64'));

        print ("Image Downloaded !! "+str(sequence));

        myCursor.execute("""INSERT into images values(%s,%s,%s,%s,%s)""",(new_image_id,current_campaign,"PostINC_Camps/"+str(current_campaign)+"/"+str(new_image_id)+".jpeg",delay,mobile));
       
        myCursor.execute("""UPDATE campaigns set count_images=count_images+1 where campaign_id=%s;""",(current_campaign));

        #count_projectors=request.form["count_projectors"];
                #count_projectors=int(count_projectors);
                #print("Extracted projectors count");
                #for i in range(0,count_projectors):
                    #projector_name=request.form["projector"+str(i)];
                        #myCursor.execute("""UPDATE projectors set current_campaign=%s where projector_id=%s""",(current_campaign,projector_name));
                        #content={};
                        #content={"campaign_id":current_campaign,"Image":encodedImage};
                        #socketIO_Object.emit(projector_name+"_img",json.dumps(content));
            #print ("Emmitteedd :"+str(i));

        connection.commit();

        return "true";

    except Exception as e:
        print "Exception "+str(e);
        return "false";

# ********************************** Fetch All User Campaigns
@app.route("/fetchAllCamps",methods=["post"])
def fetchAllCamps():
    print("Fetching campaigns ...");
    try:
        mobile=request.form["mobile"];
        myCursor.execute("""select * from campaigns where user_mobile=%s;""",(mobile));
        resultSet=myCursor.fetchall();
        payload=[];
        for row in resultSet:
            content={"Campaign_ID":row[0],"Campaign_Name":row[5]};
            payload.append(content);
        content={"Campaigns":payload};
        return json.dumps(content);
        print "Fetch Complete!";
    except Exception as e:
        print str(e);

# *********************************** Sending Campaign
@app.route("/sendCampaigns",methods=["POST"])
def createNewCampaign():
    try:
            i=0;
            count_projectors=request.form["count_projectors"];
            count_campaigns=request.form["count_campaigns"];
            print("After extracting camp ids count");
            #print ("NEW = :"+str(new_campaign_id));

            #print("Image Counts Incremented in Campaign Id "+str(new_campaign_id));
           
            count_projectors=int(count_projectors);
            print("After extracting projectors count");
           

            for i in range(0,int(count_campaigns)):   
                print("Inside loop");
                campaign_id=request.form["campaign"+str(i)];
                print("Extracted camp id");
                duration=request.form["duration"];
                print("After extracting duration");
                myCursor.execute("""select * from images where campaign_id=%s;""",(campaign_id));
                resultSet=myCursor.fetchall();
                rowcount=0;
                print("Rowcount="+str(len(myCursor.fetchall())));
                sequence=0;
                for v in resultSet:
                    rowcount=rowcount+1;

                for j in resultSet:
                    print("About to open image");
                    print("Filepath "+j[2]);
                    with open("/home/sagar_rpandav/BeamINC/"+j[2], "rb") as image_file:
                        print("Opening img...");
                        #encoded_string = base64.b64encode(image_file.read());
                        stringgg=image_file.read()
                        encoded_string=stringgg.encode('base64');
                        print "Image encodedImage";
                        for k in range(0,count_projectors):
                            print("Inside Projector Loop");
                            projector_name=request.form["projector"+str(k)];
                            print("Got Projector "+str(k));
                            content={"campaign_id":i,"image":encoded_string,"sequence":sequence,"delay":j[3],"duration":duration,"no_of_camp":count_campaigns,"no_of_images":rowcount};
                            socketIO_Object.emit(projector_name+"_img",json.dumps(content));
                            sequence=sequence+1;
                            print("Emmit to "+projector_name+" done!");
                            time.sleep(2);
            connection.commit();


            #socketIO_Object.emit("1_imad",image_string);
           

            print("All changes commited!");
            return "Done";       


    except Exception as e:
        print "Exception "+str(e);


@app.route("/addToRentableProjectors",methods=["POST"])
def viecsdscfsddwAvailableProj():
    try:
        proj_id=request.form["projector_id"];
        myCursor.execute("""update projectors set available_rent_flag=1 where projector_id=%s""",(proj_id));
        connection.commit();
        return "true";
    except Exception as e:
        return "false";


@app.route("/removeFromRentableProjectors",methods=["POST"])
def viewAvailablcsdcasdcsadaseProj():
    try:
        proj_id=request.form["projector_id"];
        myCursor.execute("""update projectors set available_rent_flag=0 where projector_id=%s""",(proj_id));
        connection.commit();
        return "true";
    except Exception as e:
        return "false";


@app.route("/getAvailableProjectors",methods=["POST"])
def viewAvailableProj():
    user_mobile=request.form["user_mobile"];
    myCursor.execute("""select * from projectors where client_mobile=%s""",(user_mobile));
    payload=[];
    resultSet=myCursor.fetchall();
    for i in resultSet:
        content={"name":i[1],"id":i[0]};
        payload.append(content);
    print str(payload);
    return json.dumps(payload);


@app.route("/getRentableProjectors",methods=["POST"])
def viewRentableProj():
    #user_mobile=request.form["user_mobile"];
    myCursor.execute("select * from projectors where available_rent_flag=1");
    payload=[];
    resultSet=myCursor.fetchall();
    for i in resultSet:
        content={"name":i[1],"id":i[0],"owner_mobile":i[2]};
        payload.append(content);
    print str(payload);
    return json.dumps(payload);


@app.route("/getRentableProjectorsPerOwner",methods=["POST"])
def viewRentableProjdff():
    user_mobile=request.form["user_mobile"];
    print("user_mobile="+str(user_mobile));
    myCursor.execute("""select * from projectors where available_rent_flag=1 and owner_mobile=%s;""",(user_mobile));
    payload=[];
    resultSet=myCursor.fetchall();
    for i in resultSet:
        content={"name":i[1],"id":i[0],"owner_mobile":i[2]};
        payload.append(content);
    print str(payload);
    return json.dumps(payload);



@app.route("/requestForProjector",methods=["POST"])
def createNewRequest():
    client_mobile=request.form["client_mobile"];
    owner_mobile=request.form["owner_mobile"];
    projector_id=request.form["projector_id"];

    myCursor.execute("""select * from projectors where projector_id=%s""",(projector_id));
    row=myCursor.fetchone();
    if(row[6]=="1"):
        myCursor.execute("select max(request_id) from requests");
        row=myCursor.fetchone();
        request_id=int(row[0]);
        request_id=request_id+1;
        myCursor.execute("""insert into requests values(%s,%s,%s,%s,0)""",(request_id,owner_mobile,client_mobile,projector_id));
        connection.commit();

        return "true";
    else:
        return "false";

@app.route("/viewAllRequestsOwner",methods=["POST"])
def getMyRequests():
    owner_mobile=request.form["owner_mobile"];
    myCursor.execute("""select * from requests where owner_mobile=%s""",(owner_mobile));
    resultSet=myCursor.fetchall();
    payload=[];
    for i in resultSet:
        content={"request_id":i[0],"projector_id":[3],"client_mobile":i[2]};
        payload.append(content);

    print str(payload);
    return json.dumps(payload);

@app.route("/viewAllRequestsClient",methods=["POST"])
def seeMyRequests():
    print("SEE MY REQ");

@app.route("/grantRequest",methods=["POST"])
def grant():
    request_id=request.form["request_id"];
    client_mobile=request.form["client_mobile"];
    projector_id=request.form["projector_id"];
    myCursor.execute("""update projectors set client_mobile=%s ,available_rent_flag=0 where projector_id=%s;""",(client_mobile,projector_id));
    myCursor.execute("""update requests set approved_flag=1 where request_id=%s;""",(request_id));
    connection.commit();
    return "true";

@app.route("/revokeRequest",methods=["POST"])
def revoke():
    request_id=request.form["request_id"];
    owner_mobile=request.form["owner_mobile"];
    projector_id=request.form["projector_id"];
    myCursor.execute("""update projectors set client_mobile=%s ,available_rent_flag=0 where projector_id=%s;""",(owner_mobile,projector_id));
    myCursor.execute("""update requests set approved_flag=0 where request_id=%s;""",(request_id));
    connection.commit();
    return "true";

if (__name__=="__main__"):
    socketIO_Object.run(app,debug=True,host='0.0.0.0');
