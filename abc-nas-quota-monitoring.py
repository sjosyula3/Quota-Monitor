import requests # To make GET and PUT requests to the Isilon.
from requests.auth import HTTPBasicAuth # Basic Authentication,to the Isilon
from texttable import Texttable
import getpass

# Specify a site "alias name", and the isilon smartconnect FQDN (system zone) followed by the correct port number
abc_sites_isilon_info = [('Site1','URL1'),
                        ('Site2','URL2'),]

# This list, will store all of the quotas that are 80% full - and will have to be increased.
quotas_to_bump = list()
# This list will store all quotas that have errors in their hard or soft quota.
quotas_with_errors = list()

# The following tables will be used to display the Path info that needs to be bumped or reviewed
display_table = Texttable()
display_table.header(['Datacenter','Increase-Quota-for-following-NAS-Volumes','Total Capacity','% Full'])

display_table_2 = Texttable()
display_table_2.header(['Datacenter','Quota-Configuration-is-Incorrect'])

# Ask for credentials.
# Make sure the user is a member of a role that can perform, HTTP calls to isilon API
print('\n')
monitor_username = input('What is your username : ')
monitor_password = getpass.getpass('What is your password : ')
print('------------------------------------------------- \n ')


def incrase_quota(url_prefix,quotaid,soft,hard):

    soft_proposed = int(soft + (soft * 0.20))
    hard_proposed = int(hard + (hard * 0.20))
    quota_increase_request_body = {"thresholds":{"soft_grace": 432000,
                                                 "soft": soft_proposed,
                                                 "hard":hard_proposed,
                                                 }}
    requests.packages.urllib3.disable_warnings()
    isilon_request = requests.put(url_prefix + '/platform/1/quota/quotas/'+quotaid,
                                  auth=HTTPBasicAuth(monitor_username ,monitor_password),
                                  json=quota_increase_request_body,
                                  verify=False)
    print('Hard and Soft quota increased by 20 % ')


# Perform a comprehensive site survey of all sites within
print('Starting Site survey ...')
for abc_site,url_prefix in abc_sites_isilon_info:
    requests.packages.urllib3.disable_warnings()
    isilon_request = requests.get(url_prefix + '/platform/1/quota/quotas',
                                  auth=HTTPBasicAuth(monitor_username ,monitor_password),
                                  verify=False)
    all_quotas = isilon_request.json()['quotas']
    for quota in all_quotas:
        site_query = abc_site
        quota_id = quota['id']
        quota_path = quota['path']
        quota_hard_limit = quota['thresholds']['hard']
        quota_soft_limit = quota['thresholds']['soft']
        quota_current_usage = int(quota['usage']['logical'])


        try:
            alert_size = quota_hard_limit * 0.80
            if quota_current_usage > alert_size:
                quotas_to_bump.append((site_query, quota_id, quota_path, quota_soft_limit,quota_hard_limit,))
                display_table.add_row([abc_site,quota_path,
                                       str(round((quota_hard_limit/1073741824),2)) + ' GB',
                                       str(round((quota_soft_limit/quota_hard_limit)*100)) + ' %'])

        except TypeError:
            display_table_2.add_row([abc_site, quota_path])
            continue
    print('Site survey complete for : ',site_query)

print('-------------------------------------------------')
print('\n \n')
print('Following NAS Volumes are alteast 80% full')
print(display_table.draw())
print('\n \n')
print('Please review the following NAS Volumes, that are running low on the available space.')
print('#####################################################################################')

# quotas_to_bump - is a list that has the quota information that has to be reviewd by the user.
#print(quotas_to_bump)



# loop through the quotas_to_bump list.
for review_item in quotas_to_bump:
    site_name,quota_id,ifs_path,soft_quota_current,hard_quota_current = review_item # Unpack the review item

    # Ask user to extent the quota - or not. Will prompt until one of  - y,n,yes,no is obtained
    asktoextend = ''
    while(asktoextend.lower() not in ['y','yes','n','no']):
        print('\nAt site {} \nThe following directory at quota is atleast 80% full : {}'.format(site_name,ifs_path))
        asktoextend = input('Do you want to extend the available capacity by 20 % ? : [y or n] : ')

    # If a yes is obtained as user input, extend the quota
    if asktoextend.lower() == 'y' or asktoextend.lower() == 'yes':
        # Refer to the site info and obtain the url with which the call has to be made.
        for site in abc_sites_isilon_info:
            alias, url = site
            if alias is site_name:
                final_url = url
        # call the quota expansion function.
        incrase_quota(final_url,quota_id,soft_quota_current,hard_quota_current)
        #print('Quotaextended')
        print('----------------------------------------------------')
        continue

    elif asktoextend.lower() == 'n' or asktoextend.lower() == 'no':
        print('This directory quota will not be extended : ', ifs_path)
        print('-----------------------------------------------------')
        continue


print('\n \n')
print('The hard or soft quota information is not available for the following NAS Volumes.\nPlease review manually and re-run Site survey')
print(display_table_2.draw())
print('\n \n')
print('End of Site Survey and Review')
