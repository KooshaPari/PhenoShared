/* AE authoring canary: editable procedural comp. Run only in a dedicated authorized app session.
   Not a headless authoring promise. Render the resulting AEP with the qualified aerender executable.
   No typography/font dependencies, footage downloads or existing-project edits. */
(function(){
 if(app.project&&app.project.numItems>0)throw new Error('Dedicated empty project required; refusing to alter existing work');
 var folder=Folder.selectDialog('Select dedicated job output folder');if(!folder)throw new Error('Cancelled');
 var projectFile=new File(folder.fsName+'/pd-motion-canary.aep');if(projectFile.exists)throw new Error('Output already exists');
 app.newProject();app.beginUndoGroup('phenoDesign motion canary');
 try{
  var comp=app.project.items.addComp('pd-motion-canary',1280,720,1,4,30);
  comp.layers.addSolid([0.04,0.07,0.08],'Background',1280,720,1,4);
  var shape=comp.layers.addShape();shape.name='Editable vector prop';
  var group=shape.property('ADBE Root Vectors Group').addProperty('ADBE Vector Group');
  group.property('ADBE Vectors Group').addProperty('ADBE Vector Shape - Ellipse').property('ADBE Vector Ellipse Size').setValue([180,180]);
  group.property('ADBE Vectors Group').addProperty('ADBE Vector Graphic - Fill').property('ADBE Vector Fill Color').setValue([0.49,0.73,0.71,1]);
  shape.property('ADBE Transform Group').property('ADBE Position').setValueAtTime(0,[300,360]);
  shape.property('ADBE Transform Group').property('ADBE Position').setValueAtTime(4,[980,360]);
  app.project.save(projectFile);
 }finally{app.endUndoGroup();}
}());
