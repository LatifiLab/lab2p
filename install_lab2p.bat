@echo off
echo ==========================================
echo Installing lab2p environment
echo ==========================================

echo Checking if environment exists...

call conda env list | findstr /C:"my_suite2p_env" >nul
if %errorlevel%==0 (
    echo Environment my_suite2p_env already exists.
) else (
    echo Creating environment my_suite2p_env...
    call conda env create -f environment.yml
)

echo Activating environment...
call conda activate my_suite2p_env

echo Installing lab2p package...
pip install -e .

echo ==========================================
echo Installation finished
echo ==========================================

echo Testing installation...
python -c "import lab2p; print('lab2p version:', lab2p.__version__)"

pause