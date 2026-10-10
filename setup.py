from setuptools import setup, find_packages
setup(
    name='llf_erpnext',
    version='1.0.0',
    description='ERPNext customizations for Learning Links Foundation',
    author='Learning Links Foundation',
    author_email='ajay.kumar@learninglinksindia.org',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=['frappe'],
)
