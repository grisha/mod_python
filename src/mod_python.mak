############################################################################
# This makefile builds mod_python on Win32 with Visual C++ 6.0
#
# Simplified mod_python build procedure:
#
# 1. Adapt APACHESRC and PYTHONSRC below 
#    or set the corresponding environment variables to override
# 2. Type 'nmake -f mod_python.mak' to build mod_python.dll in 
#    the Release directory
#
############################################################################
# BEGIN configuration variables
#
# APACHESRC is the 'src' dir of the Apache 1.3.x source distribution
# $(APACHESRC)\CoreR\ApacheCore.lib must exist.
!IF "$(APACHESRC)" == ""
APACHESRC=c:\Apache\src
!ENDIF
#
# PYTHONSRC is the python installation directory
# $(PYTHONSRC)\include and $(PYTHONSRC)\libs must exist.
!IF "$(PYTHONSRC)" == ""
PYTHONSRC=c:\Python20
!ENDIF
#
!MESSAGE APACHESRC=$(APACHESRC)
!MESSAGE PYTHONSRC=$(PYTHONSRC)
#
# END configuration variables
############################################################################

# Microsoft Developer Studio Generated NMAKE File, Based on mod_python.dsp
!IF "$(CFG)" == ""
CFG=mod_python - Win32 Release
#!MESSAGE No configuration specified. Defaulting to mod_python - Win32 Release.
!ENDIF 

!IF "$(CFG)" != "mod_python - Win32 Release" && "$(CFG)" != "mod_python - Win32 Debug"
!MESSAGE Invalid configuration "$(CFG)" specified.
!MESSAGE You can specify a configuration when running NMAKE
!MESSAGE by defining the macro CFG on the command line. For example:
!MESSAGE 
!MESSAGE NMAKE /f "mod_python.mak" CFG="mod_python - Win32 Debug"
!MESSAGE 
!MESSAGE Possible choices for configuration are:
!MESSAGE 
!MESSAGE "mod_python - Win32 Release" (based on "Win32 (x86) Dynamic-Link Library")
!MESSAGE "mod_python - Win32 Debug" (based on "Win32 (x86) Dynamic-Link Library")
!MESSAGE 
!ERROR An invalid configuration is specified.
!ENDIF 

!IF "$(OS)" == "Windows_NT"
NULL=
!ELSE 
NULL=nul
!ENDIF 

!IF  "$(CFG)" == "mod_python - Win32 Release"

OUTDIR=.\Release
INTDIR=.\Release
# Begin Custom Macros
OutDir=.\Release
# End Custom Macros

ALL : "$(OUTDIR)\mod_python.dll"


CLEAN :
	-@erase "$(INTDIR)\_apachemodule.obj"
	-@erase "$(INTDIR)\connobject.obj"
	-@erase "$(INTDIR)\mod_python.obj"
	-@erase "$(INTDIR)\requestobject.obj"
	-@erase "$(INTDIR)\serverobject.obj"
	-@erase "$(INTDIR)\tableobject.obj"
	-@erase "$(INTDIR)\util.obj"
	-@erase "$(INTDIR)\vc60.idb"
	-@erase "$(INTDIR)\Version.res"
	-@erase "$(OUTDIR)\mod_python.dll"
	-@erase "$(OUTDIR)\mod_python.exp"
	-@erase "$(OUTDIR)\mod_python.lib"

"$(OUTDIR)" :
    if not exist "$(OUTDIR)/$(NULL)" mkdir "$(OUTDIR)"

CPP=cl.exe
CPP_PROJ=/nologo /MD /W3 /GX /O2 /I "include" /I "$(PYTHONSRC)\include" /I "$(APACHESRC)\include" /D "WIN32" /D "NDEBUG" /D "_WINDOWS" /Fp"$(INTDIR)\mod_python.pch" /YX /Fo"$(INTDIR)\\" /Fd"$(INTDIR)\\" /FD /c 

.c{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cpp{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cxx{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.c{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cpp{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cxx{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

MTL=midl.exe
MTL_PROJ=/nologo /D "NDEBUG" /mktyplib203 /win32 
RSC=rc.exe
RSC_PROJ=/l 0x409 /fo"$(INTDIR)\Version.res" /d "NDEBUG" 
BSC32=bscmake.exe
BSC32_FLAGS=/nologo /o"$(OUTDIR)\mod_python.bsc" 
BSC32_SBRS= \
	
LINK32=link.exe
LINK32_FLAGS=ApacheCore.lib ws2_32.lib /nologo /dll /incremental:no /pdb:"$(OUTDIR)\mod_python.pdb" /machine:I386 /out:"$(OUTDIR)\mod_python.dll" /implib:"$(OUTDIR)\mod_python.lib" /libpath:"$(APACHESRC)\CoreR" /libpath:"$(PYTHONSRC)\libs" 
LINK32_OBJS= \
	"$(INTDIR)\_apachemodule.obj" \
	"$(INTDIR)\connobject.obj" \
	"$(INTDIR)\mod_python.obj" \
	"$(INTDIR)\requestobject.obj" \
	"$(INTDIR)\serverobject.obj" \
	"$(INTDIR)\tableobject.obj" \
	"$(INTDIR)\util.obj" \
	"$(INTDIR)\Version.res"

"$(OUTDIR)\mod_python.dll" : "$(OUTDIR)" $(DEF_FILE) $(LINK32_OBJS)
    $(LINK32) @<<
  $(LINK32_FLAGS) $(LINK32_OBJS)
<<

!ELSEIF  "$(CFG)" == "mod_python - Win32 Debug"

OUTDIR=.\Debug
INTDIR=.\Debug
# Begin Custom Macros
OutDir=.\Debug
# End Custom Macros

ALL : "$(OUTDIR)\mod_python.dll"


CLEAN :
	-@erase "$(INTDIR)\_apachemodule.obj"
	-@erase "$(INTDIR)\connobject.obj"
	-@erase "$(INTDIR)\mod_python.obj"
	-@erase "$(INTDIR)\requestobject.obj"
	-@erase "$(INTDIR)\serverobject.obj"
	-@erase "$(INTDIR)\tableobject.obj"
	-@erase "$(INTDIR)\util.obj"
	-@erase "$(INTDIR)\vc60.idb"
	-@erase "$(INTDIR)\vc60.pdb"
	-@erase "$(INTDIR)\Version.res"
	-@erase "$(OUTDIR)\mod_python.dll"
	-@erase "$(OUTDIR)\mod_python.exp"
	-@erase "$(OUTDIR)\mod_python.ilk"
	-@erase "$(OUTDIR)\mod_python.lib"
	-@erase "$(OUTDIR)\mod_python.pdb"

"$(OUTDIR)" :
    if not exist "$(OUTDIR)/$(NULL)" mkdir "$(OUTDIR)"

CPP=cl.exe
CPP_PROJ=/nologo /MDd /W3 /Gm /GX /ZI /Od /I "include" /I "$(PYTHONSRC)\include" /I "$(APACHESRC)\include" /D "WIN32" /D "_DEBUG" /D "_WINDOWS" /Fp"$(INTDIR)\mod_python.pch" /YX /Fo"$(INTDIR)\\" /Fd"$(INTDIR)\\" /FD /GZ /c 

.c{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cpp{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cxx{$(INTDIR)}.obj::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.c{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cpp{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

.cxx{$(INTDIR)}.sbr::
   $(CPP) @<<
   $(CPP_PROJ) $< 
<<

MTL=midl.exe
MTL_PROJ=/nologo /D "_DEBUG" /mktyplib203 /win32 
RSC=rc.exe
RSC_PROJ=/l 0x409 /fo"$(INTDIR)\Version.res" /d "_DEBUG" 
BSC32=bscmake.exe
BSC32_FLAGS=/nologo /o"$(OUTDIR)\mod_python.bsc" 
BSC32_SBRS= \
	
LINK32=link.exe
LINK32_FLAGS=ApacheCore.lib ws2_32.lib /nologo /dll /incremental:yes /pdb:"$(OUTDIR)\mod_python.pdb" /debug /machine:I386 /out:"$(OUTDIR)\mod_python.dll" /implib:"$(OUTDIR)\mod_python.lib" /pdbtype:sept /libpath:"$(APACHESRC)\CoreD" /libpath:"$(PYTHONSRC)\libs" 
LINK32_OBJS= \
	"$(INTDIR)\_apachemodule.obj" \
	"$(INTDIR)\connobject.obj" \
	"$(INTDIR)\mod_python.obj" \
	"$(INTDIR)\requestobject.obj" \
	"$(INTDIR)\serverobject.obj" \
	"$(INTDIR)\tableobject.obj" \
	"$(INTDIR)\util.obj" \
	"$(INTDIR)\Version.res"

"$(OUTDIR)\mod_python.dll" : "$(OUTDIR)" $(DEF_FILE) $(LINK32_OBJS)
    $(LINK32) @<<
  $(LINK32_FLAGS) $(LINK32_OBJS)
<<

!ENDIF 


!IF "$(NO_EXTERNAL_DEPS)" != "1"
!IF EXISTS("mod_python.dep")
!INCLUDE "mod_python.dep"
!ELSE 
!MESSAGE Warning: cannot find "mod_python.dep"
!ENDIF 
!ENDIF 


!IF "$(CFG)" == "mod_python - Win32 Release" || "$(CFG)" == "mod_python - Win32 Debug"
SOURCE=.\_apachemodule.c

"$(INTDIR)\_apachemodule.obj" : $(SOURCE) "$(INTDIR)"


SOURCE=.\connobject.c

"$(INTDIR)\connobject.obj" : $(SOURCE) "$(INTDIR)"


SOURCE=.\mod_python.c

"$(INTDIR)\mod_python.obj" : $(SOURCE) "$(INTDIR)"


SOURCE=.\requestobject.c

"$(INTDIR)\requestobject.obj" : $(SOURCE) "$(INTDIR)"


SOURCE=.\serverobject.c

"$(INTDIR)\serverobject.obj" : $(SOURCE) "$(INTDIR)"


SOURCE=.\tableobject.c

"$(INTDIR)\tableobject.obj" : $(SOURCE) "$(INTDIR)"


SOURCE=.\util.c

"$(INTDIR)\util.obj" : $(SOURCE) "$(INTDIR)"


SOURCE=.\Version.rc

"$(INTDIR)\Version.res" : $(SOURCE) "$(INTDIR)"
	$(RSC) $(RSC_PROJ) $(SOURCE)



!ENDIF 

