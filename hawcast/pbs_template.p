### Standard Output
#PBS -N [jobname]
#PBS -o [pbsoutdir]/[jobname].out
### Standard Error
#PBS -e [pbsoutdir]/[jobname].err
#PBS -W umask=0003
### Maximum wallclock time format HOURS:MINUTES:SECONDS
#PBS -l walltime=[walltime]
#PBS -l nodes=1:ppn=1
### Queue name
#PBS -q workq

# ==============================================================================
# single PBS mode: one case per PBS job
# evaluates to true if LAUNCH_PBS_MODE is NOT set
if [ -z ${LAUNCH_PBS_MODE+x} ] ; then
  ### Create scratch directory and copy data to it
  cd $PBS_O_WORKDIR
  echo "current working dir (pwd):"
  pwd
  cp -R ./[modelzip] /scratch/$USER/$PBS_JOBID
fi
# ==============================================================================


# ==============================================================================
# single PBS mode: one case per PBS job
# evaluates to true if LAUNCH_PBS_MODE is NOT set
if [ -z ${LAUNCH_PBS_MODE+x} ] ; then
  echo
  echo 'Execute commands on scratch nodes'
  cd /scratch/$USER/$PBS_JOBID
  # create unique dir for each CPU
  mkdir "1"; cd "1"
  pwd
  /usr/bin/unzip ../[modelzip]
  mkdir -p [htcdir]
  mkdir -p [resdir]
  mkdir -p [logdir]
  mkdir -p [turbdir]
  cp -R $PBS_O_WORKDIR/[htcdir]/[jobname].htc ./[htcdir]
  cp -R $PBS_O_WORKDIR/[turbdir][turbfileroot]*.bin [turbdir]
  _HOSTNAME_=`hostname`
  if [[ ${_HOSTNAME_:0:1} == "j" ]] ; then
    WINEARCH=win64 WINEPREFIX=~/.wine winefix
  fi
# ==============================================================================

# ------------------------------------------------------------------------------
# find+xargs mode: 1 PBS job, multiple cases
else
  # with find+xargs we first browse to CPU folder
  cd "$CPU_NR"
fi
# ------------------------------------------------------------------------------

echo ""
# ==============================================================================
# single PBS mode: one case per PBS job
# evaluates to true if LAUNCH_PBS_MODE is NOT set
if [ -z ${LAUNCH_PBS_MODE+x} ] ; then
  echo "execute HAWC2, fork to background"
  time WINEARCH=win64 WINEPREFIX=~/.wine wine hawc2-latest ./[htcdir]/[jobname].htc &
  wait
# ==============================================================================

# ------------------------------------------------------------------------------
# find+xargs mode: 1 PBS job, multiple cases
else
  echo "execute HAWC2, do not fork and wait"
  (time WINEARCH=win64 WINEPREFIX=~/.wine numactl --physcpubind=$CPU_NR wine hawc2-latest ./[htcdir]/[jobname].htc) 2>&1 | tee [pbsoutdir]/[jobname].err.out
fi
# ------------------------------------------------------------------------------


### Epilogue
# ==============================================================================
# single PBS mode: one case per PBS job
# evaluates to true if LAUNCH_PBS_MODE is NOT set
if [ -z ${LAUNCH_PBS_MODE+x} ] ; then
  ### wait for jobs to finish
  wait
  echo ""
  echo "Copy back from scratch directory"
  mkdir -p $PBS_O_WORKDIR/[resdir]
  mkdir -p $PBS_O_WORKDIR/[logdir]
  mkdir -p $PBS_O_WORKDIR/animation/
  mkdir -p $PBS_O_WORKDIR/[turbdir]
  cp -R [resdir]. $PBS_O_WORKDIR/[resdir].
  cp -R [logdir]. $PBS_O_WORKDIR/[logdir].
  cp -R animation/. $PBS_O_WORKDIR/animation/.

  echo ""
  echo "COPY BACK TURB IF APPLICABLE"
  cd turb/
  for i in `ls *.bin`; do  if [ -e $PBS_O_WORKDIR/[turbdir]$i ]; then echo "$i exists no copyback"; else echo "$i copyback"; cp $i $PBS_O_WORKDIR/[turbdir]; fi; done
  cd /scratch/$USER/$PBS_JOBID/1/
  echo "END COPY BACK TURB"
  echo ""

  echo "COPYBACK [copyback_files]/[copyback_frename]"
  echo "END COPYBACK"
  echo ""
  echo ""
  echo "following files are on node/cpu 1 (find .):"
  find .
# ==============================================================================
# ------------------------------------------------------------------------------
# find+xargs mode: 1 PBS job, multiple cases
else
  cd /scratch/$USER/$PBS_JOBID/$CPU_NR/
  rsync -a --remove-source-files [resdir]. ../HAWC2SIM/[resdir].
  rsync -a --remove-source-files [logdir]. ../HAWC2SIM/[logdir].
  rsync -a --remove-source-files [pbsoutdir]/. ../HAWC2SIM/[pbsoutdir]/.
  rsync -a --remove-source-files animation/. ../HAWC2SIM/animation/.

  echo ""
  echo "COPY BACK TURB IF APPLICABLE"
  cd turb/
  for i in `ls *.bin`; do  if [ -e $PBS_O_WORKDIR/[turbdir]$i ]; then echo "$i exists no copyback"; else echo "$i copyback"; cp $i $PBS_O_WORKDIR/[turbdir]; fi; done
  cd /scratch/$USER/$PBS_JOBID/$CPU_NR/
  echo "END COPY BACK TURB"
  echo ""

  echo "COPYBACK [copyback_files]/[copyback_frename]"
  echo "END COPYBACK"
  echo ""
# ------------------------------------------------------------------------------
fi
exit
