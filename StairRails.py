import math
import inkex
import copy
import numpy
from inkex import PathElement, Style
from inkex.paths import Path,Move,Line,ZoneClose
from inkex.transforms import BoundingBox,Vector2d
from inkex.elements._groups import Group

#--------------------copied code
class pathStruct(object):
    def __init__(self):
        self.id="path0000"
        self.path=Path()
        self.enclosed=False
        self.style = None
    def __str__(self):
        return self.path
    
class pnPoint(object):
   # This class came from https://github.com/JoJocoder/PNPOLY
    def __init__(self,p):
        self.p=p
    def __str__(self):
        return self.p
    def InPolygon(self,polygon,BoundCheck=False):
        inside=False
        if BoundCheck:
            minX=polygon[0][0]
            maxX=polygon[0][0]
            minY=polygon[0][1]
            maxY=polygon[0][1]
            for p in polygon:
                minX=min(p[0],minX)
                maxX=max(p[0],maxX)
                minY=min(p[1],minY)
                maxY=max(p[1],maxY)
            if self.p[0]<minX or self.p[0]>maxX or self.p[1]<minY or self.p[1]>maxY:
                return False
        j=len(polygon)-1
        for i in range(len(polygon)):
            if ((polygon[i][1]>self.p[1])!=(polygon[j][1]>self.p[1]) and (self.p[0]<(polygon[j][0]-polygon[i][0])*(self.p[1]-polygon[i][1])/( polygon[j][1] - polygon[i][1] ) + polygon[i][0])):
                    inside =not inside
            j=i
        return inside

        

class StairRails(inkex.EffectExtension):
    def add_arguments(self, pars):
        pars.add_argument("--usermenu")

        pars.add_argument("--unit", default="in",\
            help="Dimensional units")
        pars.add_argument("--staircase_width", type=float, default=2.0,\
            help="width of staircase in dimensional units")	
        pars.add_argument("--staircase_height", type=float, default=2.0,\
            help="height of staircase in dimensional units")	
        pars.add_argument("--staircase_depth", type=float, default=3.0,\
            help="depth(front to back) of staircase in dimensional units")	
        pars.add_argument("--numstairs", type=int, default=3,\
            help="Number stairs (risers)")
        pars.add_argument("--landing_length", type=float, default=2.0,\
            help="length -  side to side -  of landing in dimensional units")
        pars.add_argument("--landing_depth", type=float, default=1.0,\
            help="depth of landing - front to back - in dimensional units MUST be >0 if there is a landing_length>0")
        pars.add_argument("--rail_height", type=float, default=1.0,\
            help="railing height in dimensional units")			
        pars.add_argument("--rails_per_step", type=int, default=2,\
            help="Number of rails uprights per step (sets approx. railing thickness) in dimensional units")
        pars.add_argument("--railgap_ratio", type=float, default=60,\
            help="percentage of distance the rail takes vs the gap between")
        pars.add_argument("--off_center_distance", type=float, default=0.0,\
            help="offset of staircase from landing 0 is center -  in dimensional units")	
        pars.add_argument("--door_width", type=float, default=2.0,\
            help="width of door opening in back rail --  in dimensional units")		
        pars.add_argument("--door_off_center_distance", type=float, default=0.0,\
            help="distance off-center for door opening in back railing--  in dimensional units")	
        pars.add_argument("--dashlength", type=float, default=0.1,\
            help="Length of dashline in dimensional units (zero for solid line)")
        pars.add_argument("--tabangle", type=float, default=45.0,\
            help="Angle of tab edges in degrees")
        pars.add_argument("--tabheight", type=float, default=0.4,\
            help="Height of tab in dimensional units")
        pars.add_argument("--maketoprail", type=inkex.Boolean, dest="maketoprail",\
            help = "Force construction of back rail when landing width is staircase width")
        pars.add_argument("--rail_thick", type=float, default=10.0,\
            help="Thickness of top and bottom part of rail, as a percentage of rail height")   
        pars.add_argument("--bottomgap", type=float, default=0.2,\
            help="Gap height underneath rail --  in dimensional units")	


    def drawline(self, dstr, name, parent, sstr=None):
        line_style   = {'stroke':'#000000','stroke-width':'0.25','fill':'#eeeeee'}
        if sstr == None:
            stylestr = str(Style(line_style))
        else:
            stylestr = sstr
        el = parent.add(PathElement())
        el.path = dstr
        el.style = stylestr
        el.label = name

    def pathInsidePath(self, path, testpath):
        enclosed = True
        for tp in testpath:
            # If any point in the testpath is outside the path, it's not enclosed
            if self.insidePath(path, tp) == False:
                enclosed = False
                return enclosed # True if testpath is fully enclosed in path
        return enclosed
        
    def insidePath(self, path, p):
        point = pnPoint((p.x, p.y))
        pverts = []
        for pnum in path:
            if pnum.letter == 'Z':
                pverts.append((path[0].x, path[0].y))
            else:
                pverts.append((pnum.x, pnum.y))
        isInside = point.InPolygon(pverts, True)
        return isInside # True if point p is inside path

    def makescore(self, pt1, pt2, dashlength):
        # Draws a dashed line of dashlength between two points
        # Dash = dashlength space followed by dashlength mark
        # if dashlength is zero, we want a solid line
        # Returns dashed line as a Path object
        apt1 = Line(0.0,0.0)
        apt2 = Line(0.0,0.0)
        ddash = Path()
        if math.isclose(dashlength, 0.0):
            #inkex.utils.debug("Draw solid dashline")
            ddash.append(Move(pt1.x,pt1.y))
            ddash.append(Line(pt2.x,pt2.y))
        else:
            if math.isclose(pt1.y, pt2.y):
                #inkex.utils.debug("Draw horizontal dashline")
                if pt1.x < pt2.x:
                    xcushion = pt2.x - dashlength
                    xpt = pt1.x
                    ypt = pt1.y
                else:
                    xcushion = pt1.x - dashlength
                    xpt = pt2.x
                    ypt = pt2.y
                done = False
                while not(done):
                    if (xpt + dashlength*2) <= xcushion:
                        xpt = xpt + dashlength
                        ddash.append(Move(xpt,ypt))
                        xpt = xpt + dashlength
                        ddash.append(Line(xpt,ypt))
                    else:
                        done = True
            elif math.isclose(pt1.x, pt2.x):
                #inkex.utils.debug("Draw vertical dashline")
                if pt1.y < pt2.y:
                    ycushion = pt2.y - dashlength
                    xpt = pt1.x
                    ypt = pt1.y
                else:
                    ycushion = pt1.y - dashlength
                    xpt = pt2.x
                    ypt = pt2.y
                done = False
                while not(done):
                    if(ypt + dashlength*2) <= ycushion:
                        ypt = ypt + dashlength         
                        ddash.append(Move(xpt,ypt))
                        ypt = ypt + dashlength
                        ddash.append(Line(xpt,ypt))
                    else:
                        done = True
            else:
                #inkex.utils.debug("Draw sloping dashline")
                if pt1.y > pt2.y:
                    apt1.x = pt1.x
                    apt1.y = pt1.y
                    apt2.x = pt2.x
                    apt2.y = pt2.y
                else:
                    apt1.x = pt2.x
                    apt1.y = pt2.y
                    apt2.x = pt1.x
                    apt2.y = pt1.y
                m = (apt1.y-apt2.y)/(apt1.x-apt2.x)
                theta = math.atan(m)
                msign = (m>0) - (m<0)
                ycushion = apt2.y + dashlength*math.sin(theta)
                xcushion = apt2.x + msign*dashlength*math.cos(theta)
                xpt = apt1.x
                ypt = apt1.y
                done = False
                while not(done):
                    nypt = ypt - dashlength*2*math.sin(theta)
                    nxpt = xpt - msign*dashlength*2*math.cos(theta)
                    if (nypt >= ycushion) and (((m<0) and (nxpt <= xcushion)) or ((m>0) and (nxpt >= xcushion))):
                        # move to end of space / beginning of mark
                        xpt = xpt - msign*dashlength*math.cos(theta)
                        ypt = ypt - msign*dashlength*math.sin(theta)
                        ddash.append(Move(xpt,ypt))
                        # draw the mark
                        xpt = xpt - msign*dashlength*math.cos(theta)
                        ypt = ypt - msign*dashlength*math.sin(theta)
                        ddash.append(Line(xpt,ypt))
                    else:
                        done = True
        return ddash

    def detectIntersect(self, x1, y1, x2, y2, x3, y3, x4, y4):
        td = (x1-x2)*(y3-y4)-(y1-y2)*(x3-x4)
        if td == 0:
            # These line segments are parallel
            return False
        t = ((x1-x3)*(y3-y4)-(y1-y3)*(x3-x4))/td
        if (0.0 <= t) and (t <= 1.0):
            return True
        else:
            return False

    def orientTab(self,pt1,pt2,height,angle,theta,orient):
        tpt1 = Line(0.0,0.0)
        tpt2 = Line(0.0,0.0)
        tpt1.x = pt1.x + orient[0]*height + orient[1]*height/math.tan(math.radians(angle))
        tpt2.x = pt2.x + orient[2]*height + orient[3]*height/math.tan(math.radians(angle))
        tpt1.y = pt1.y + orient[4]*height + orient[5]*height/math.tan(math.radians(angle))
        tpt2.y = pt2.y + orient[6]*height + orient[7]*height/math.tan(math.radians(angle))
        if not math.isclose(theta, 0.0):
            t11 = Path([Move(pt1.x,pt1.y),Line(tpt1.x, tpt1.y)])
            t12 = Path([Move(pt1.x,pt1.y),Line(tpt2.x, tpt2.y)])
            thetal1 = t11.rotate(theta, [pt1.x,pt1.y])
            thetal2 = t12.rotate(theta, [pt2.x,pt2.y])
            tpt1.x = thetal1[1].x
            tpt1.y = thetal1[1].y
            tpt2.x = thetal2[1].x
            tpt2.y = thetal2[1].y
        return tpt1,tpt2

    def makeTab(self, tpath, pt1, pt2, tabht, taba):
        # tpath - the pathstructure containing pt1 and pt2
        # pt1, pt2 - the two points where the tab will be inserted
        # tabht - the height of the tab
        # taba - the angle of the tab sides
        # returns the two tab points (Line objects) in order of closest to pt1
        tpt1 = Line(0.0,0.0)
        tpt2 = Line(0.0,0.0)
        currTabHt = tabht
        currTabAngle = taba
        testAngle = 1.0
        testHt = currTabHt * 0.001
        adjustTab = 0
        tabDone = False
        while not tabDone:
            # Let's find out the orientation of the tab
            if math.isclose(pt1.x, pt2.x):
                # It's vertical. Let's try the right side
                if pt1.y < pt2.y:
                    pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,0.0,[1,0,1,0,0,1,0,-1])
                    if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                       (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[-1,0,-1,0,0,1,0,-1]) # Guessed wrong
                    else:
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[1,0,1,0,0,1,0,-1]) # Guessed right
                else: # pt2.y < pt1.y
                    pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,0.0,[1,0,1,0,0,-1,0,1])
                    if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                       (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[-1,0,-1,0,0,-1,0,1]) # Guessed wrong
                    else:
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[1,0,1,0,0,-1,0,1]) # Guessed right
            elif math.isclose(pt1.y, pt2.y):
                # It's horizontal. Let's try the top
                if pt1.x < pt2.x:
                    pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,0.0,[0,1,0,-1,-1,0,-1,0])
                    if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                       (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[0,1,0,-1,1,0,1,0]) # Guessed wrong
                    else:
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[0,1,0,-1,-1,0,-1,0]) # Guessed right
                else: # pt2.x < pt1.x
                    pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,0.0,[0,-1,0,1,-1,0,-1,0])
                    if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                       (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[0,-1,0,1,1,0,1,0]) # Guessed wrong
                    else:
                        tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,0.0,[0,-1,0,1,-1,0,-1,0]) # Guessed right

            else: # the orientation is neither horizontal nor vertical
                # Let's get the slope of the line between the points
                # Because Inkscape's origin is in the upper-left corner,
                # a positive slope (/) will yield a negative value
                slope = (pt2.y - pt1.y)/(pt2.x - pt1.x)
                # Let's get the angle to the horizontal
                theta = math.degrees(math.atan(slope))
                # Let's construct a horizontal tab
                seglength = math.sqrt((pt1.x-pt2.x)**2 +(pt1.y-pt2.y)**2)
                if slope < 0.0:
                    if pt1.x < pt2.x:
                        pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,theta,[0,1,0,-1,-1,0,-1,0])
                        if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                           (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,1,0,-1,1,0,1,0]) # Guessed wrong
                        else:
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,1,0,-1,-1,0,-1,0]) # Guessed right
                    else: # pt1.x > pt2.x
                        pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,theta,[0,-1,0,1,-1,0,-1,0])
                        if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                           (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,-1,0,1,1,0,1,0]) # Guessed wrong
                        else:
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,-1,0,1,-1,0,-1,0]) # Guessed right
                else: # slope > 0.0
                    if pt1.x < pt2.x:
                        pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,theta,[0,1,0,-1,-1,0,-1,0])
                        if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                           (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,1,0,-1,1,0,1,0]) # Guessed wrong
                        else:
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,1,0,-1,-1,0,-1,0]) # Guessed right
                    else: # pt1.x > pt2.x
                        pnpt1,pnpt2 = self.orientTab(pt1,pt2,testHt,testAngle,theta,[0,-1,0,+1,-1,0,-1,0])
                        if ((not tpath.enclosed) and (self.insidePath(tpath.path, pnpt1) or self.insidePath(tpath.path, pnpt2))) or \
                           (tpath.enclosed and ((not self.insidePath(tpath.path, pnpt1)) and (not self.insidePath(tpath.path, pnpt2)))):
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,-1,0,1,1,0,1,0]) # Guessed wrong
                        else:
                            tpt1,tpt2 = self.orientTab(pt1,pt2,currTabHt,currTabAngle,theta,[0,-1,0,1,-1,0,-1,0]) # Guessed right
            # Check to see if any tabs intersect each other
            if self.detectIntersect(pt1.x, pt1.y, tpt1.x, tpt1.y, pt2.x, pt2.y, tpt2.x, tpt2.y):
                # Found an intersection.
                if adjustTab == 0:
                    # Try increasing the tab angle in one-degree increments
                    currTabAngle = currTabAngle + 1.0
                    if currTabAngle > 88.0: # We're not increasing the tab angle above 89 degrees
                        adjustTab = 1
                        currTabAngle = taba
                if adjustTab == 1:
                    # So, try reducing the tab height in 20% increments instead
                    currTabHt = currTabHt - tabht*0.2 # Could this lead to a zero tab_height?
                    if currTabHt <= 0.0:
                        # Give up
                        currTabHt = tabht
                        adjustTab = 2
                if adjustTab == 2:
                    tabDone = True # Just show the failure
            else:
                tabDone = True
            
        return tpt1,tpt2     
    #-------------------end copied code
    def geo_a_b_beta(self,a,b):
        c=math.sqrt(a**2 + b**2)
        beta=math.asin(b/c)
        return math.degrees(beta)
    
    def geo_a_beta_c(self,a, beta):
        c = a/math.cos(math.radians(a))
        return (c)
    def geo_a_beta_b(self,a,beta):
        b = a * math.tan(math.radians(beta))
        return b
        
    def signbit(self,n):
        signbit = 1 if n < 0 else -1
        return signbit
    
    def effect(self):
        layer = self.svg.get_current_layer()
        scale =self.svg.unittouu('1'+self.options.unit)
        sidepath = pathStruct()
        backpath = pathStruct()
        backpatha = pathStruct()
        landrail = pathStruct()
        railstairs=pathStruct()
        railing = pathStruct()
        upright = pathStruct()
        toprail = pathStruct()
        tbup = pathStruct()
        tbpath = Path()
        btbpath = Path()
        dscore = Path()
        dscore1 = Path()
        bscore1 = Path()
        bscore = Path()
        railscore = Path()
        s = []
        wrap_style = {'stroke':'#000000','stroke-width':'0.25','fill':'#ffdddd'}
        #re-assign all the input variables from options strings
        staircase_width = float(self.options.staircase_width)*scale
        staircase_height = float(self.options.staircase_height)*scale
        staircase_depth = float(self.options.staircase_depth)*scale
        numstairs = int(self.options.numstairs)
        landing_length  = float(self.options.landing_length)*scale
        landing_depth = float(self.options.landing_depth)*scale
        rail_height = float(self.options.rail_height)*scale
        rails_per_step  = int(self.options.rails_per_step)
        railgap_ratio = float(self.options.railgap_ratio)/100
        off_center_distance = float(self.options.off_center_distance)*scale
        door_width = float(self.options.door_width)*scale
        door_off_center_distance = float(self.options.door_off_center_distance)*scale
        dashlength = float(self.options.dashlength)*scale
        tab_angle = float(self.options.tabangle)
        tabheight = float(self.options.tabheight)*scale
        maketoprail = bool(self.options.maketoprail)
        rail_thick = float(self.options.rail_thick)
        bottomgap = float(self.options.bottomgap)*scale
        
        fingerwidth = tabheight  #for calculating the hole area on the back piece
        #figure out tread depth  
        tread_depth = staircase_depth/(numstairs-1)
        tread_width = staircase_width
        
        # Multiply the input by appropriate scaling
        #Calculate:
        #	Using the tread depth, calculate the rail_width and gaprail_length for steps
        #	example: if tread is 1" deep and 2 rails per step with a railgap_ratio of 40% (leaving 60% for gaps)
        #	one inch will have a total of 2 rails and 2 gaps. 
        #	divide the percentage by the number of rails, in this case 2. 
        #	So rails will be 20% of 1 inch, and gaps will be 30% of one inch.
        #	formula is: 	
        #RAILS
        onerail = tread_depth/rails_per_step  #one rail and gap group
        
        rail_width = railgap_ratio * onerail  #of that, the rail is n%
        gap_width = onerail-rail_width
        is_wide_landing = 0
        gaprail_length = rail_width+gap_width
      
        if (landing_depth < tread_depth):
            landing_depth = tread_depth    #top step is landing
            
            
            
        if (landing_length > staircase_width):
            is_wide_landing = 1
            
        #This is the exact number we will use for rails, but since the landing may not be a multiple of step depth, we need to adjust the gap width to accommodate.
        #gaprail is the set of one gap and one rail
        
        #Get an approximate number of gaprails needed for the landing depth, including an extra rail at both ends.

           
        #If the landing is wider than the stairs, we also need to calculate the gaprail_length_n for that
        # nominal is based on tread depth
        if is_wide_landing:
        
            #sanity checks
            if abs(off_center_distance) > landing_length - staircase_width:
                off_center_distance = (landing_length - staircase_width) * self.signbit(off_center_distance)
            if abs(door_off_center_distance) > landing_length - door_width:
                door_center_distance = (landing_length - door_width) * self.signbit(door_off_center_distance)    
                
            land3_width = ((landing_length-tread_width)/2) + off_center_distance   #front right
            land4_width = ((landing_length-tread_width)/2) - off_center_distance   #frontleft 
            #if there is a right side rail then figure how to fit. 
            land5_width = ((landing_depth-door_width)/2) + door_off_center_distance   #back right 
            land6_width = ((landing_depth-door_width)/2) - door_off_center_distance   #back left
            
            
           

        # now the stairs 

        #need to start by drawing the landing/first tread 
        #if the landing_length >0  [and] landing_length > tread_width then rather than draw the first tread, we will be drawing the landing
        # this will add two nodes IF the landing_length > tread_width
        #if there is no landing, the piece will be a rectangle  with tabs on all sides and scorelines on each.  The stairs will start with a tread and end with a riser.
        # the rectangle for the stairs will be (riser_height+tread_depth) * numstairs  by stair_width
        # store points in list of Vector2d()
        #	tread_depth
        #	tread_width
        #	riser height
        #if there is no wide landing the stairway needs to have the starting y value as -landing_depth

        riser_height = staircase_height/numstairs
        # ignore landing that make no sense: if wider, but not longer, or if landing is narrower than tread.
        sanecheck  = True
        no_landing = 1
        
        stepslip = 0
        starty = 0
        startx = 0
        if landing_length < tread_width:
            landing_length = tread_width
        
               
        tread_depth = staircase_depth/(numstairs-1)  #adjust because the top tread is part of the landing
        if landing_length > tread_width :  #it is wider and deeper
            stepslip = 2  # to deal with the extra two nodes 
            
            xs = ((landing_length/2)-(tread_width/2)) + off_center_distance +tread_width #we want our actual staircase at 0,0
            xsave = xs
            ys = -landing_depth
            s.append( Vector2d(xs,ys))
            ys = 0
            s.append( Vector2d(xs,ys))  #we've moved down the first side of the landing
            is_wide_landing = 1
             
        else:
            #just need to extend the first and last nodes upward  but same number of nodes
            starty = -landing_depth
            is_wide_landing = 0
            xs = 0
            ys = starty
                
            
        downspace = [tread_depth,riser_height]
        srange = ((numstairs)*2)+1 #nodes on right side are 0 through srange
        k = 0
        k2 = 0
        sfix = False
        if not(is_wide_landing):
            k=0     #we start with a tread but it needs to be as deep as the landing_depth for the first one
            sfix = True
            srange = ((numstairs)*2)+1#nodes on right side are 0 through srange
        else :
            k = 1   #we start with a riser, not a tread
            k2 = 1  #need to ads the extra nodes
            srange = (numstairs*2)+k2 #nodes on right side are 0 through srange
        xs = tread_width
        ys = starty
        
       
        for i in range(srange-is_wide_landing):
            
            s.append( Vector2d(xs,ys))   #the upper right of staircase 
            if sfix:
                ys += landing_depth
                sfix = False
            else:
                ys += downspace[k]  #needs to alternate with tread_depth 
            k = abs(int(1-k))
            
        leftside = (numstairs*2)+is_wide_landing	

        
        if is_wide_landing:
            m= srange 
        else:
            m=srange -1
       

        for i in range(srange - is_wide_landing):    #because we handle the last two separately if there's a wide landing
            #work way back up 
            xs = 0			
            ys = s[m].y    # get the opposite side corresponding y value index
            #decrement  for next one
            s.append(Vector2d(xs,ys))
            m = m-1 
        if is_wide_landing:   #we still have two nodes to handle
            #last two nodes are bottom left of landing and top left of landing
            xs = xsave - landing_length
            ys = 0
            s.append(Vector2d(xs,ys))
            ys = -landing_depth
            s.append(Vector2d(xs,ys))

        #now build the steps piece into a pathStruct that we need for adding tabs and scorelines

        for i in range (len(s)):
            if i==0:
                sidepath.path.append(Move(s[i].x,s[i].y))
            else:
                sidepath.path.append(Line(s[i].x,s[i].y))
        sidepath.path.append(ZoneClose())
        # scorelines and  tabs path

        tblen = len(sidepath.path)
        ss = len(s)-1
        ss2 = (numstairs*2) +1   
        #add the score lines between the nodes
        
        for i in range(1+is_wide_landing,ss2):
            cpt1 = sidepath.path[i]     
            cpt2 = sidepath.path[ss-i]	
            dscore1 = dscore1 + self.makescore(cpt1, cpt2,dashlength)
        wscore = dscore1
        #add the tabs
        tbpath.append(copy.deepcopy(sidepath.path[0]))
        
        for j in range(1,tblen)  :
            cpt1 = sidepath.path[j-1]  #Move or Line
            cpt2 = sidepath.path[j]    #Line or Z
            
            if cpt2.letter == 'Z':
                cpt2 = Line(sidepath.path[0].x,sidepath.path[0].y) #use first point
            tabpt1, tabpt2 = self.makeTab(sidepath, cpt1, cpt2, tabheight, tab_angle)
            tbpath.append(tabpt1)
            tbpath.append(tabpt2)
            tbpath.append(cpt2)
            
            dscore = dscore + self.makescore(cpt1, cpt2,dashlength)  #this is the scoreline for the tab
        tbpath.append(copy.deepcopy(sidepath.path[j]))
        dscore1 = dscore + dscore1	
        
        #MAKE BACK
        # back is a rectangle with tabs on the left and right only
        backpath.path.clear()
        if is_wide_landing:
            xv = landing_length
        else:
            xv = staircase_width
        
        yv = staircase_height
        backpath.path.append(Move(0,0))
        backpath.path.append(Line(xv,0))
        backpath.path.append(Line(xv,yv))
        backpath.path.append(Line(0,yv))
        backpath.path.append(ZoneClose())
        
        #looks OK
        btbpath.append(copy.deepcopy(backpath.path[0]))
        for j in range(1,len(backpath.path))  :
           
            
            bcpt1 = backpath.path[j-1]  #Move or Line
            bcpt2 = backpath.path[j]    #Line or Z
            
            if bcpt2.letter == 'Z':
                bcpt2 = Line(backpath.path[0].x,backpath.path[0].y) #use first point
            if j != 1:
                btabpt1, btabpt2 = self.makeTab(backpath, bcpt1, bcpt2, tabheight, tab_angle)
                btbpath.append(btabpt1)
                btbpath.append(btabpt2)
                btbpath.append(bcpt2)                
                bscore = bscore + self.makescore(bcpt1, bcpt2,dashlength)  #this is the scoreline for the tab
            else:
                btbpath.append(bcpt2)  
        if  ((landing_length>3*fingerwidth) or (staircase_width> 3*fingerwidth)) and (staircase_height> 3*fingerwidth):
            makehole = True
            finger = fingerwidth*1.5
            btbpath.append(copy.deepcopy(backpath.path[j]))   
            bscore1 = bscore + bscore1	
            xscale = (xv-finger*2)/xv
            yscale= (yv-finger*2)/yv
            ringpath = (backpath.path.scale(xscale,yscale))
            ringpath = ringpath.reverse()
            ringpath = ringpath.translate(finger,finger)
            btbpath= btbpath+ringpath
        else: 
            makehole = False
           
        #now concatenate or group        
        if math.isclose(dashlength, 0.0):
                               
                # lump together all the score lines
                stairgroup = Group()
                stairgroup.label = 'stairgroup'
                self.drawline(str(tbpath),'stairsmodel',stairgroup) # Output the model for stairs
                if dscore != '':
                    self.drawline(str(dscore1),'stairscores',stairgroup) # Output the scorelines for stairs
                layer.append(stairgroup)
                
                backgroup = Group()
                backgroup.label = 'groupback'
                self.drawline(str(btbpath),'back',backgroup) # Output the models for the back 
                if (bscore1 != '') and (makehole == True):
                    self.drawline(str(bscore1),'backscore',backgroup) # Output the back scorelines separately
                layer.append(backgroup)
                 
        else:
                tbpath = tbpath + dscore1
                self.drawline(str(tbpath),'stairway',layer)
                if (bscore1 != '') and (makehole == True):
                    btbpath = btbpath+bscore1
                self.drawline(str(btbpath),'back',layer)
                
          
        
                
        #END BACK 
                
        #draw wrapper
        self.drawline(str(backpath.path),'backwrapper',layer,wrap_style)
        sidepath.path = sidepath.path + wscore
        self.drawline(str(sidepath.path),'stairwrapper',layer,wrap_style)
                
                
        #now we figure out the sides, bottom, back and rails  
        
        #if there is a wide landing then make the side pieces for the landing separately
        #LEFT LANDING SIDE
        if is_wide_landing:  
            btbpath.clear()
            backpath.path.clear()
            tbpath.clear()
            score = ""
            score1 = ""
            xv = 0
            yv = 0
            backpath.path.append(Move(0,0))
            backpath.path.append(Line(landing_depth,0))
            backpath.path.append(Line(landing_depth+land4_width,0))
            backpath.path.append(Line(landing_depth+land4_width,staircase_height))
            backpath.path.append(Line(landing_depth,staircase_height))
            backpath.path.append(Line(0,staircase_height))
            backpath.path.append(ZoneClose())
            #score middle
            cpt1 = backpath.path[1]
            cpt2 = backpath.path[4]
            score1 = self.makescore(cpt1,cpt2,dashlength)
            
          
            if math.isclose(dashlength, 0.0):
                    leftlandg = Group()
                    leftlandgw = Group()
                    leftlandg.label = 'leftlandg'
                    leftlandgw.label = 'leftlandgw'
                    self.drawline(str(backpath.path),'leftside_landing',leftlandg) # Output the model
                    self.drawline(str(backpath.path),'leftside_landing_wrapper',leftlandgw,wrap_style) # Output the wrapper
                    if score1 != '':
                        self.drawline(str(score1),'leftscore1',leftlandg) # Output the scorelines separately
                        self.drawline(str(score1),'leftscore1w',leftlandgw) # Output the scorelines separately
                    layer.append(leftlandg)
                    layer.append(leftlandgw)
                     
            else:
                    backpath.path = backpath.path + score1
                    self.drawline(str(backpath.path),'leftside_landing',layer)
                    self.drawline(str(backpath.path),'leftside_landing_wrapper',layer,wrap_style)
                    
        #RIGHT LANDING SIDE            
        if is_wide_landing:  
            btbpath.clear()
            backpath.path.clear()
            tbpath.clear()
            score = ""
            score1 = ""
            xv = 0
            yv = 0
            backpath.path.append(Move(0,0))
            backpath.path.append(Line(-landing_depth,0))
            backpath.path.append(Line(-(landing_depth+land3_width),0))
            backpath.path.append(Line(-(landing_depth+land3_width),staircase_height))
            backpath.path.append(Line(-landing_depth,staircase_height))
            backpath.path.append(Line(0,staircase_height))
            backpath.path.append(ZoneClose())
            #score middle
            cpt1 = backpath.path[1]
            cpt2 = backpath.path[4]
            score1 = self.makescore(cpt1,cpt2,dashlength)
            
            
            if math.isclose(dashlength, 0.0):
                    rtlandg = Group()
                    rtlandgw = Group()
                    rtlandg.label = 'rtlandg'
                    rtlandgw.label = 'rtlandgw'
                    self.drawline(str(backpath.path),'right side landing',rtlandg) # Output the model
                    self.drawline(str(backpath.path),'right side wrapper',rtlandgw,wrap_style) # Output the model
                    if score1 != '':
                        self.drawline(str(score1),'rightscore1',rtlandg) # Output the scorelines separately
                        self.drawline(str(score1),'rightscore1w',rtlandgw) # Output the scorelines separately
                    layer.append(rtlandg)
                    layer.append(rtlandgw)
                     
            else:
                    backpath.path = backpath.path + score1
                    self.drawline(str(backpath.path),'right_landing_side',layer)
                    self.drawline(str(backpath.path),'right_landing_side_wrapper',layer,wrap_style)
                    
                    
        #now do the stair sides
        
        # FIRST STAIR SIDE 
        btbpath.clear()
        backpath.path.clear()
        bscore.clear()
        k=0
        stairct = 2*numstairs
        startx = 0
        starty = 0 
        jstart = 1
        firstadd = 1
        addstep = -1
        if not(is_wide_landing):
            firstadd = landing_depth-tread_depth
            addstep = 1
        backpath.path.append(Move(startx,starty))
        downspace = [tread_depth,riser_height]
        for j in range(jstart,stairct + addstep):
            xv = backpath.path[j-1].x
            yv = backpath.path[j-1].y
            if j>1:
                firstadd = 0
            if k==0 : #tread                
                backpath.path.append(Line(xv+downspace[k]+firstadd,yv))
            else: #riser
                backpath.path.append(Line(xv,downspace[k]+yv))
            k=abs(1-k)
        #now at bottom right of staircase shape so traverse to bottom left
        lasty = backpath.path[len(backpath.path)-1].y
        backpath.path.append(Line(startx,lasty))
        backpath.path.append(ZoneClose())
        #ADD TAB ON BACK OF THIS PIECE
                
         #looks OK
        btbpath.append(copy.deepcopy(backpath.path[0]))
        
        for j in range(1,len(backpath.path))  :
           
            
            bcpt1 = backpath.path[j-1]  #Move or Line
            bcpt2 = backpath.path[j]    #Line or Z
            
            if bcpt2.letter == 'Z':
                bcpt2 = Line(backpath.path[0].x,backpath.path[0].y) #use first point
            if (j == len(backpath.path)-1 ) and (is_wide_landing):
                btabpt1, btabpt2 = self.makeTab(backpath, bcpt1, bcpt2, tabheight, tab_angle)
                btbpath.append(btabpt1)
                btbpath.append(btabpt2)
                btbpath.append(bcpt2)                
                bscore = bscore + self.makescore(bcpt1, bcpt2,dashlength)  #this is the scoreline for the tab
            else:
                btbpath.append(bcpt2)  
            
        btbpath.append(copy.deepcopy(backpath.path[j]))   
        
        
        #now concatenate or group        
        if math.isclose(dashlength, 0.0):
                               
                # lump together all the score lines
                stairsidegrp1 = Group()
                stairsidegrp1.label = 'stairside1_group'
                self.drawline(str(btbpath),'stairside1',stairsidegrp1) # Output the model for stairside
                if bscore != '':
                    self.drawline(str(bscore),'stair_side1',stairsidegrp1) # Output the scorelines for stairs
                layer.append(stairsidegrp1)
        else:
                btbpath = btbpath + bscore
                self.drawline(str(btbpath),'stairside1',layer)
        #draw wrapper
        self.drawline(str(backpath.path),'stairside1_wrapper',layer,wrap_style)
        
        
        
        #make a mirror
        btbpath.clear()
        bscore.clear()
        for j in range(len(backpath.path)):
            if backpath.path[j].letter =='Z':
                backpatha.path.append(ZoneClose())
            else:
                xa = -(backpath.path[j].x)
                ya = backpath.path[j].y
                if j == 0:
                    backpatha.path.append(Move(xa,ya))
                else:
                    backpatha.path.append(Line(xa,ya))
        #ADD TAB ON BACK OF STAIRCASE SIDE 
        
         #looks OK
        btbpath.append(copy.deepcopy(backpatha.path[0]))
        
        for j in range(1,len(backpatha.path))  :
           
            
            bcpt1 = backpatha.path[j-1]  #Move or Line
            bcpt2 = backpatha.path[j]    #Line or Z
            
            if bcpt2.letter == 'Z':
                bcpt2 = Line(backpatha.path[0].x,backpatha.path[0].y) #use first point
            if (j == len(backpatha.path)-1 ) and (is_wide_landing):
                btabpt1, btabpt2 = self.makeTab(backpatha, bcpt1, bcpt2, tabheight, tab_angle)
                btbpath.append(btabpt1)
                btbpath.append(btabpt2)
                btbpath.append(bcpt2)                
                bscore = bscore + self.makescore(bcpt1, bcpt2,dashlength)  #this is the scoreline for the tab
            else:
                btbpath.append(bcpt2)  
            
        btbpath.append(copy.deepcopy(backpatha.path[j]))   
        
        
        #now concatenate or group        
        if math.isclose(dashlength, 0.0):
                               
                # lump together all the score lines
                stairsidegrp2 = Group()
                stairsidegrp2.label = 'stairsidegroup2'
                self.drawline(str(btbpath),'stair_side2',stairsidegrp2) # Output the model for stairside
                if bscore != '':
                    self.drawline(str(bscore),'stair_sidescores2',stairsidegrp2) # Output the scorelines for stairs
                layer.append(stairsidegrp2)
        else:
                btbpath = btbpath + bscore
                self.drawline(str(btbpath),'stairway',layer)
                
        #draw wrapper
        self.drawline(str(backpatha.path),'stairside2_wrapper',layer,wrap_style)
        
        
        #END ADD TAB ON BACK OF STAIRCASE SIDE
            
       
       

       #BOTTOM
        backpath.path.clear()
        tbpath.clear()
        dscore.clear()
        dscore1.clear() 
        omit = [3,7]
        if is_wide_landing: 
            
            xv = staircase_width
            yv = landing_depth
            backpath.path.append(Move(-xv,0))  #draw from top of staircase leftside 
            
            if land4_width >0 :  #there is a landing on the left, move left
                xv = land4_width+xv
                backpath.path.append(Line(-xv,0))
                backpath.path.append(Line(-xv,-yv))
            else:  #othewise move up
                backpath.path.append(Line(-xv,-yv))
            xv = -xv+landing_length  
            backpath.path.append(Line(xv,-yv))  #no need for door gap on bottom piece
            backpath.path.append(Line(xv,0))    #now at bottom right
            if xv > 0  :                #draw back to zero if not there already 
                backpath.path.append(Line(0,0))
                    #finally, draw around staircase bottom starting from 0,0 
            xv=staircase_width
            backpath.path.append(Line(0,staircase_depth))
            backpath.path.append(Line(-xv,staircase_depth))
            backpath.path.append(ZoneClose())
            
            #self.drawline(str(backpath.path),'bottomwrapper',layer)
              
        else:       #not a wide landing so the bottom will be a rectangle
            xv = staircase_width              
            yv = landing_depth
            backpath.path.append(Move(xv, 0))
            backpath.path.append(Line(xv,staircase_depth+landing_depth))
            backpath.path.append(Line(0,staircase_depth+landing_depth))
            backpath.path.append(Line(0,0))
            backpath.path.append(ZoneClose())
            omit=[2,4]
            
            
    
        
        #add tabs
        tbpath.append(copy.deepcopy(backpath.path[0]))
        for j in range(1,len(backpath.path)):
            cpt1 = backpath.path[j-1]  #Move or Line
            cpt2 = backpath.path[j]    #Line or Z
            if cpt2.letter == 'Z':
                cpt2 = Line(backpath.path[0].x,backpath.path[0].y) #use first point
            if (j!=omit[0]) and (j != omit[1]):
                tabpt1, tabpt2 = self.makeTab(backpath, cpt1, cpt2, tabheight, tab_angle)
                tbpath.append(tabpt1)
                tbpath.append(tabpt2)
                tbpath.append(cpt2)
                dscore = dscore + self.makescore(cpt1, cpt2,dashlength)  #this is the scoreline for the tab
            else:
                tbpath.append(cpt2)
        tbpath.append(copy.deepcopy(backpath.path[j]))    
        #draw the bottom
    
        if math.isclose(dashlength, 0.0):
            # lump together all the score lines
            btmgrp = Group()
            btmgrp.label = 'btmgrp'
            self.drawline(str(tbpath),'bottom',btmgrp) # Output the model for stairs
            if dscore != '':
                self.drawline(str(dscore),'btmscores',btmgrp) # Output the scorelines for stairs
            layer.append(btmgrp)
        
        else:
            tbpath = tbpath + dscore
            self.drawline(str(tbpath),'bottom',layer)
            

        #_______________________________________________________________________
            
        #make rails
        
        #SETUP Vars
        rail_height2 = rail_height - bottomgap #allows for small gap between rail and rail footings
        rail_thick = (rail_thick/100) * rail_height2
        cutheight = rail_height2 - (2*rail_thick)
        upright_ht = rail_height2 + bottomgap  #uprights will be separate pieces glued in place
        upright_long_ht = upright_ht+riser_height
        onerail = tread_depth / rails_per_step
        gap_width = railgap_ratio * onerail
        rail_width = onerail-gap_width
        rname = ["left","right"]
        rnamenum = 0
        #variables needed for stair rails:
        dbeta = (self.geo_a_b_beta(staircase_depth,(staircase_height-riser_height)))  #rail angle
        dr = self.geo_a_beta_b(rail_width,dbeta)   #distance skip down across rail
        dg = self.geo_a_beta_b(gap_width,dbeta)    #distance skip down across gap
        
        #draw a non_wide landing depth railing
        pt0 = Vector2d(0, -(staircase_height + rail_height))
        pt1 = Vector2d(staircase_depth, -(riser_height + rail_height))
        pt2 = Vector2d(staircase_depth, pt1.y + rail_height2)
        pt3 = Vector2d(pt0.x, pt0.y + rail_height2)
        
        pt1a = Vector2d(pt1.x+rail_width,pt1.y + dr)
        pt2a = Vector2d(pt2.x+rail_width, pt2.y+dr)   
        
        pax = -(landing_depth )
        pay = - (staircase_height + rail_height2 + bottomgap)
        pat0 = Vector2d(pax,pay)
        pat1 = Vector2d(pat0.x+landing_depth,pat0.y)
        pat2 = Vector2d(pat1.x,pat1.y+rail_height2)
        pat3 = Vector2d(pat0.x, pat2.y)
            

        if not(is_wide_landing): #join  to make one railing outer piece 
            #draw a non_wide landing depth railing
            
            landrail.path.append(Move(pat0.x,pat0.y))
            landrail.path.append(Line(pat1.x,pat1.y))
            landrail.path.append(Line(pt1a.x,pt1a.y))
            landrail.path.append(Line(pt2a.x,pt2a.y))
            landrail.path.append(Line(pat2.x,pat2.y))
            landrail.path.append(Line(pat3.x,pat3.y))
            landrail.path.append(ZoneClose())
            
            
        else:   
            #first draw the steps railing only 
            
            #landrail.path.append(Move(pat0.x,pat0.y))
            landrail.path.append(Move(pat1.x,pat1.y))
            landrail.path.append(Line(pt1a.x,pt1a.y))
            landrail.path.append(Line(pt2a.x,pt2a.y))
            landrail.path.append(Line(pat2.x,pat2.y))
            #landrail.path.append(Line(pat3.x,pat3.y))
            landrail.path.append(ZoneClose())
            
            
            x0 = pt0.x  - gap_width
            y0 = (pt0.y) - dg
            for i in range((numstairs-1)*rails_per_step):
                #draw a gap and close it
                x0 += gap_width +rail_width
                x1 = x0 + gap_width
                y0 += dr+dg
                y0b = y0+rail_thick
                y1 = y0+dg
                y1b= y1+rail_thick
                landrail.path.append(Move(x0,y0b))
                landrail.path.append(Line(x0,y0b+cutheight))
                landrail.path.append(Line(x1,y1b+cutheight))
                landrail.path.append(Line(x1,y1b))            
                landrail.path.append(ZoneClose())
        
            #build all the separate railing pieces using the lengths -- stored in widelen[]
            #These are used if there is a wide landing.           
            rightfront = ((landing_length-tread_width)/2) + off_center_distance   
            leftfront  = ((landing_length-tread_width)/2) - off_center_distance  
            if door_width == 0:
                rightback = 0
                leftback = landing_length
            else:
                rightback  = ((landing_length-door_width)/2) - door_off_center_distance 
                leftback  = ((landing_length-door_width)/2) + door_off_center_distance 
            leftside = landing_depth
            rightside = landing_depth
            
            widelen = [leftback, leftside, leftfront, rightback, rightside,rightfront]
            
            widenames = ["leftbackrail","leftsiderail","leftfrontrail","rightbackrail","rightsiderail","rightfrontrail"]
            onerail = tread_depth / rails_per_step
            gap_width = railgap_ratio * onerail
            rail_width = onerail-gap_width
            gapsw = []
            gapsr =[]
            rs=[Vector2d(0,0),Vector2d(0,0)]
            #each of the two  pieces has up to 8 nodes -- less if there is a zero length front or back
            for j in range(6):
                #set up the array to hold the gap widths gapsw[] and the gap_rail widths gapsr[]
                if widelen[j]>0:
                    
                    cnum = int(widelen[j] // onerail)
                    cnum2 = widelen[j] % onerail
                    if cnum > 0:
                        gapadd = cnum2/cnum
                    else:
                        gapadd = -cnum
                        
                    gapsw.append(gap_width+gapadd)
                    gapsr.append(rail_width + gapsw[j])
                else:  #this piece has no length
                    gapsw.append(0)
                    gapsr.append(0)
            #railscore = railscore+self.makescore(r1,r2,dashlength/2)
            for j in range(0,6,3):  #do left side then right side rails
                railscore.clear()
                railing.path.clear()
                railing.path.append(Move(0,0))
                endx = 0
                rsi = 0
                if widelen[j] >0: #first two segments are the back and we also continue over on the side bottom
                   railing.path.append(Line(widelen[j],0))
                   railing.path.append(Line(widelen[j],rail_height2))
                   railing.path.append(Line(0,rail_height2))
                   #scoreline between 0,0 and 0,rail_height2
                   railscore = railscore+self.makescore(Vector2d(0,rail_height),Vector2d(0,0),dashlength/2)
                   railing.path.append(Line(-widelen[j+1],rail_height2))  #always a so side add to bottom of shape
                   endx = -widelen[j+1]
                   rs[rsi]= Vector2d(widelen[j],0)
                   #also make a score line
                   nx = -widelen[j+1]
                   railscore = railscore+self.makescore(Vector2d(nx,0),Vector2d(nx,rail_height),dashlength/2)
                   
                    
                else: #first two segments are from the  side
                    railing.path.append(Move(widelen[j+1],0))
                    railing.path.append(Line(widelen[j+1],rail_height2))
                    railing.path.append(Line(0,rail_height2))
                    endx = 0
                    rs[rsi] = Vector2d(widelen[j+1],0)
                if widelen[j+2] >0 :
                    railing.path.append(Line((endx-widelen[j+2]),rail_height2))
                    #go up to start going back
                    railing.path.append(Line(endx+-widelen[j+2],0))
                    if endx != 0 : #we had a back and a side so draw to side
                        railing.path.append(Line(-widelen[j+1],0))
                        
                        
                else:
                    railing.path.append(Line(endx,0))
                    if endx != 0 : #we had a back and a side so draw to side
                        railing.path.append(Line(-widelen[j+1],0))
                railing.path.append(ZoneClose())
                
                #the outer shapes of the flat rails are now done
                
                
                #make the cutouts
                onerail = tread_depth / rails_per_step
                gap_width = railgap_ratio * onerail
                rail_width = onerail-gap_width
                bbrail = railing.path.bounding_box()
                rail_len = bbrail.width
                cnum = int(rail_len // onerail)
                cnum2 = rail_len % onerail
                if cnum > 0:
                    gapadd = cnum2/cnum
                else:
                    gapadd = -cnum
                gap_width2 = gap_width+gapadd
                gaprail2 = rail_width + gap_width2
                #draw a gap then rail
                p0x = -(rail_len-rs[rsi].x)
                p0y = rs[rsi].y + rail_thick 
                rpt = int((rail_len- rail_width) // gaprail2)+1
                for j in range(rpt):
                   railing.path.append(Move (p0x,p0y))
                   railing.path.append(Line (p0x,p0y+cutheight))
                   railing.path.append(Line (p0x+gap_width2,p0y+cutheight))
                   railing.path.append(Line (p0x+gap_width2,p0y))
                   railing.path.append(ZoneClose())
                   p0x += gaprail2
                   
                   
                   
                   
                #--copy
                
                if math.isclose(dashlength, 0.0):
                    railgrp = Group()
                    railgrp.label = 'railgroup'
                    
                    self.drawline(str(railing.path),'landing_rail',railgrp) # Output the model
                    
                    if railscore != '':
                        self.drawline(str(railscore),'landing_rail_score',railgrp) # Output the scorelines separately
                    layer.append(railgrp)
                     
                else:
                    
                    railing.path = railing.path + railscore
                    self.drawline(str(railing.path),'landing_rail_'+rname[rnamenum],layer)
                    rnamenum += 1
                #--endcopy
                
                
                #self.drawline(str(railing.path),"railingpath"+str(j),layer)
                rsi += 1
        if not(is_wide_landing):  # mmake the cutouts in the slant rail
            onerail = tread_depth / rails_per_step
            gap_width = railgap_ratio * onerail
            rail_width = onerail-gap_width
            cnum = int(landing_depth // onerail)
            cnum2 = landing_depth % onerail
            if cnum > 0:
                gapadd = cnum2/cnum
            else:
                gapadd = -cnum
            gap_width2 = gap_width+gapadd
            
            gaprail2 = rail_width + gap_width2
            #draw a gap then rail
            p0x = pat0.x + rail_width
            p0y = pat0.y + rail_thick 
            
            rpt = int((landing_depth - rail_width) // gaprail2)+1
            for j in range(rpt):
               landrail.path.append(Move (p0x,p0y))
               landrail.path.append(Line (p0x,p0y+cutheight))
               landrail.path.append(Line (p0x+gap_width2,p0y+cutheight))
               landrail.path.append(Line (p0x+gap_width2,p0y))
               landrail.path.append(ZoneClose())
               p0x += gaprail2
             
        
            x0 = pt0.x  - gap_width
            y0 = (pt0.y) - dg
            for i in range((numstairs-1)*rails_per_step):
                #draw a gap and close it
                x0 += gap_width +rail_width
                x1 = x0 + gap_width
                y0 += dr+dg
                y0b = y0+rail_thick
                y1 = y0+dg
                y1b= y1+rail_thick
                landrail.path.append(Move(x0,y0b))
                landrail.path.append(Line(x0,y0b+cutheight))
                landrail.path.append(Line(x1,y1b+cutheight))
                landrail.path.append(Line(x1,y1b))            
                landrail.path.append(ZoneClose())
        
            #calculate back rail if requested -- only if no wide landing
            if maketoprail:
                
                cnum2 = staircase_width % onerail
                if cnum > 0:
                    gapadd = cnum2/cnum
                else:
                    gapadd = -cnum
                gap_width2 = gap_width+gapadd
                rpt = int((staircase_width - rail_width) // gaprail2)+1
                #draw outside
                
                #draw rails
                toprail.path.append(Move (0,0))
                toprail.path.append(Line (staircase_width,0))
                toprail.path.append(Line (staircase_width,rail_height2))
                toprail.path.append(Line (0,rail_height2))
                toprail.path.append(ZoneClose())
                #draw a gap then rail
                p0x = -(0)
                p0y = rail_thick 
                rpt = int((staircase_width - rail_width) // gaprail2)+1
                for j in range(rpt):
                   toprail.path.append(Move (p0x,p0y))
                   toprail.path.append(Line (p0x,p0y+cutheight))
                   toprail.path.append(Line (p0x+gap_width2,p0y+cutheight))
                   toprail.path.append(Line (p0x+gap_width2,p0y))
                   toprail.path.append(ZoneClose())
                   p0x += gaprail2
                self.drawline(str(toprail.path),'toprail',layer)
        #try drawing it 
        self.drawline(str(landrail.path),'landrail',layer)
        
        
        #finally draw some rail connectors/ uprights 2*rail_width wide with a score line down the middle and tabs at the bottom
        upht = [rail_height,upright_long_ht,upright_long_ht,upright_long_ht]
                    
        uprightgrp = Group()
        uprightgrp2 = Group()
        uprightgrp3 = Group()
        uprightgrp4 = Group()
        upgrp =[uprightgrp,uprightgrp2,uprightgrp3,uprightgrp4]
        for j in range(4):
            upright.path.clear()
            tbup.path.clear()
            upy = upht[j]
            
            tbpath.clear()
            upright.path.append(Move(0,0))
            upright.path.append(Line(rail_width,0))
            upright.path.append(Line(rail_width*2,0))
            if j==2:
            
                #add extension to right side
                upright.path.append(Line(rail_width*2,rail_height))
                upright.path.append(Line((rail_width*4),rail_height))
                upright.path.append(Line(rail_width*4,upy))
            upright.path.append(Line(rail_width*2,upy))
            
            upright.path.append(Line(rail_width,upy))
            
            upright.path.append(Line(0,upy))
            if j==3:
            
                #add extension to left side
                upright.path.append(Line(-rail_width*2,upy))
                upright.path.append(Line(-rail_width*2,rail_height))
                upright.path.append(Line(0,rail_height))
                  
                
            upright.path.append(ZoneClose())
            if (j==2):
                dscore1 = self.makescore(upright.path[1],upright.path[7],dashlength)
                tbup.path = upright.path
            elif (j==3):
                dscore1 = self.makescore(upright.path[1],upright.path[4],dashlength)
                tbup.path = upright.path
                
            else:
                dscore1 = self.makescore(upright.path[1],upright.path[4],dashlength)
             
                tbup.path.append(Move(0,0))
                tbup.path.append(Line(rail_width,0))
                tbup.path.append(Line(rail_width*2,0))
                tbup.path.append(Line(rail_width*2,upy))
               
                cpt1 = Vector2d(rail_width*2,upy)
                cpt2 = Vector2d(rail_width,upy)
                
                dscore1 = dscore1 + self.makescore(cpt1,cpt2,dashlength/3)
                
                tabpt1,tabpt2 = self.makeTab(upright,cpt1,cpt2,tabheight,tab_angle)  #4
                tbup.path.append(tabpt1)
                tbup.path.append(tabpt2)
                tbup.path.append(Line(cpt2.x, cpt2.y)) #
                
                cpt1 = cpt2
                cpt2 = Vector2d(0,upy)
                
                dscore1 = dscore1 + self.makescore(cpt1,cpt2,dashlength/3)
                
                tabpt1,tabpt2 = self.makeTab(upright,cpt1,cpt2,tabheight,tab_angle)
                tbup.path.append(tabpt1)
                tbup.path.append(tabpt2)
                tbup.path.append(Line(cpt2.x, cpt2.y))
                
                tbup.path.append(ZoneClose())
            
            
            #and draw the upright

            if math.isclose(dashlength, 0.0):
                    g = upgrp[j]
                    
                    g.label = 'uprightgrp'+str(j)
                    
                    self.drawline(str(tbup.path),'upright'+str(j),g) # Output the model
                    
                    if dscore1 != '':
                        self.drawline(str(dscore1),'uprightscore'+str(j),g) # Output the scorelines separately
                    layer.append(g)
                     
            else:
                tbup.path = tbup.path + dscore1
                self.drawline(str(tbup.path),'upright'+str(j),layer)
         
    
            
		        
if __name__ == '__main__':
    StairRails().run()

		
	
	
		
	
	
		
		
		
		
	