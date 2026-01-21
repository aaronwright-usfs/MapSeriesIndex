# -*- coding: utf-8 -*-
## created by Aaron Wright (aaron.wright@usda.gov or aaron_wright@firenet.gov)
## on 8/31/2024

import arcpy, os

#Define project
aprx = arcpy.mp.ArcGISProject("CURRENT")

#Get user environment setting for adding tool outputs to map
outputSet = arcpy.env.addOutputsToMap

class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "Toolbox"
        self.alias = "toolbox"

        # List of tool classes associated with this toolbox
        self.tools = [MapSeriesIndex]


class MapSeriesIndex:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Create Map Series Indexes"
        self.description = "Creates a polygon feature class showing the extents of pages in a map series"

    def getParameterInfo(self):
        """
        0: Layout Name
        1: OutLoc
        2: addOut
        """

        params = [
          
            arcpy.Parameter(
                displayName = 'Map Series Layout',
                name = 'layout',
                datatype = 'layout', 
                parameterType = 'Required',
                direction = 'Input'),
           
            arcpy.Parameter(
                displayName = 'Output Feature Class',
                name = 'outputLoc',
                datatype = 'DEFeatureClass',
                parameterType = 'Required',
                direction = 'Output'),

            arcpy.Parameter(
                displayName = 'Add Indexes to Map',
                name = 'addOut',
                datatype = 'GPBoolean',
                parameterType = 'Optional',
                direction = 'Input')
            ]

        params[2].enabled = False

                
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Check user's Add Outputs setting, if not enabled, enable add output checkbox in tool dialog"""
        if not outputSet:
            parameters[2].enabled = True   
                
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        lyt = aprx.listLayouts(parameters[0].valueAsText)[0]
        bms = lyt.mapSeries
        if ((type(bms).__name__ not in ['BookmarkMapSeries', 'MapSeries'])):
            parameters[0].setErrorMessage('The selected layout must have a Spatial or Bookmark Map Series enabled.')
       
        return
    

    def execute(self, parameters, messages):
        """The source code of the tool."""
        # Define input variables
        lytName = parameters[0].valueAsText
        outFC = parameters[1].valueAsText
        addOut = parameters[2].value

      
        # Specify and return layout object and map series from user input
        lyt = aprx.listLayouts(lytName)[0]
        bms = lyt.mapSeries
               
        # Specify and return map frame that the bookmarks alter
        mf = bms.mapFrame

        # Get spatial reference of map in map Frame
        spRef = mf.map.spatialReference
        arcpy.AddMessage(f"Spatial Reference: {spRef.name}")

        # define the output name and directory separately
        outName = os.path.basename(outFC)
        outLoc = os.path.dirname(outFC)

         # Create the output feature class
        arcpy.management.CreateFeatureclass(outLoc, outName, "POLYGON", "", "", "", spRef.name)
        
        # Add fields to created feature class
        arcpy.management.AddFields(
            outFC,
            [['Name', 'TEXT', 'Name', 255, ''],
              ['Scale', 'LONG', 'Scale', '', ''],
              ['PageNum', 'LONG', 'pageNum', '', '']])
        arcpy.AddMessage(f'{outName} created in {outLoc}.')


        # Iterate through bookmarks
        for pageNum in range(1, bms.pageCount + 1):

            #set variable for page number to be populated in output feature class.
            bms.currentPageNumber = pageNum

            #If bookmark map series get bookmark name for page name, if not return map series index field
            #attribute using getattr() for page name.
            if ((type(bms).__name__ == 'BookmarkMapSeries')):
                pgName = bms.currentBookmark.name
            else:
                nmField = bms.pageNameField.name
                pgName = getattr(bms.pageRow, nmField)

            # get extent of the map frame when zoomed to current bookmark
            ext = mf.camera.getExtent()

            # get scale of the map frame when zoomed to the current bookmark
            mfScale = mf.camera.scale

            # round scale to whole number
            rndScale = round(mfScale)

            # create polygon object from extent
            polygon = ext.polygon
            
            # Define fields and values for InsertCursor function
            fields = ["SHAPE@", "Name", "Scale", "pageNum"]
            values = [polygon, pgName, rndScale, pageNum]

            # Add polygon object to output feature class and insert bookmark name and scale values in attributes
            with arcpy.da.InsertCursor(outFC, fields) as cursor:
                cursor.insertRow(values)
                arcpy.AddMessage(f'Index: {pgName} added to {outName}.')

            # Delete polygon object
            arcpy.Delete_management(polygon)

        # If the add output setting is disabled and the user checked the Add Indexes box,
        # add output and resymbolize feature class
        if addOut == True or outputSet:
            
            mf.map.addDataFromPath(outFC)
            # #define layer and adjust symbology
            lyr = mf.map.listLayers(outName)[0]
            sym = lyr.symbology
            sym.renderer.symbol.color = {'RGB' : [0, 0, 0, 0]}
            sym.renderer.symbol.outlineColor = {'RGB' : [0, 0, 0, 100]}
            sym.renderer.symbol.size = 3
            lyr.showLabels = True
            for lc in lyr.listLabelClasses():
                lc.visible = False
            
            lbl = lyr.createLabelClass(name = 'Index Name',
                                       expression = '[Name]',
                                       labelclass_language = 'Python')
            lbl.visible = True

            lyr.symbology = sym   

        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""


        return

