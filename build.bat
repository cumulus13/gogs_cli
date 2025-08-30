rmdir /s /q  dist
rmdir /s /q  build
rmdir /s /q  *.egg-info
rmdir /s /q  __pycache__
python setup.py sdist bdist_wheel
twine upload dist\* -r pypihub
twine upload dist\* 
