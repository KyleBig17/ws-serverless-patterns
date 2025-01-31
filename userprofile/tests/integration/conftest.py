# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

import boto3
import logging
import os
import pytest
import uuid
import json

APPLICATION_STACK_NAME = os.getenv('USERS_STACK_NAME', None)
MODULE4_STACK_NAME = os.getenv('USERPROFILE_STACK_NAME', None)
globalConfig = {}
LOGGER = logging.getLogger(__name__)

def get_stack_outputs(stack_name):
    result = {}
    cf_client = boto3.client('cloudformation')
    cf_response = cf_client.describe_stacks(StackName=stack_name)
    outputs = cf_response["Stacks"][0]["Outputs"]
    for output in outputs:
        result[output["OutputKey"]] = output["OutputValue"]
    return result


def create_cognito_accounts():
    result = {}
    sm_client = boto3.client('secretsmanager')
    idp_client = boto3.client('cognito-idp')
    # create regular user account
    sm_response = sm_client.get_random_password(ExcludeCharacters='"''`[]{}():;,$/\\<>|=&',
                                                RequireEachIncludedType=True)
    result["user1UserName"] = "user1User@example.com"
    result["user1UserPassword"] = sm_response["RandomPassword"]
    try:
        idp_client.admin_delete_user(UserPoolId=globalConfig["UserPool"],
                                     Username=result["user1UserName"])
    except idp_client.exceptions.UserNotFoundException:
        print('user1 user haven''t been created previously')
    idp_response = idp_client.admin_create_user(
        UserPoolId=globalConfig["UserPool"],
        Username=result["user1UserName"],
        UserAttributes=[{"Name": "name", "Value": result["user1UserName"]}],
        TemporaryPassword=result["user1UserPassword"],
        MessageAction='SUPPRESS',
        DesiredDeliveryMediums=[],
    )
    # Change the temporary password
    secrets_manager_response = sm_client.get_random_password(
        ExcludeCharacters='"''`[]{}():;,$/\\<>|=&', RequireEachIncludedType=True)
    result["user1UserPassword"] = secrets_manager_response["RandomPassword"]    
    idp_client.admin_set_user_password(
        UserPoolId=globalConfig["UserPool"],
        Username=result["user1UserName"],
        Password=result["user1UserPassword"],
        Permanent=True
    )
    result["user1UserSub"] = idp_response["User"]["Username"]

    # get new user authentication info
    idp_response = idp_client.initiate_auth(
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': result["user1UserName"],
            'PASSWORD': result["user1UserPassword"]
        },
        ClientId=globalConfig["UserPoolClient"],
    )
    result["user1UserIdToken"] = idp_response["AuthenticationResult"]["IdToken"]
    result["user1UserAccessToken"] = idp_response["AuthenticationResult"]["AccessToken"]
    result["user1UserRefreshToken"] = idp_response["AuthenticationResult"]["RefreshToken"]
    # create user2 user account
    sm_response = sm_client.get_random_password(ExcludeCharacters='"''`[]{}():;,$/\\<>|=&',
                                                RequireEachIncludedType=True)
    result["user2UserName"] = "user2User@example.com"
    result["user2UserPassword"] = sm_response["RandomPassword"]
    try:
        idp_client.admin_delete_user(UserPoolId=globalConfig["UserPool"],
                                     Username=result["user2UserName"])
    except idp_client.exceptions.UserNotFoundException:
        print('User2 user haven''t been created previously')
    idp_response = idp_client.admin_create_user(
        UserPoolId=globalConfig["UserPool"],
        Username=result["user2UserName"],
        UserAttributes=[{"Name": "name", "Value": result["user2UserName"]}],
        TemporaryPassword=result["user2UserPassword"],
        MessageAction='SUPPRESS',
        DesiredDeliveryMediums=[],
    )
    # Change the temporary password
    secrets_manager_response = sm_client.get_random_password(
        ExcludeCharacters='"''`[]{}():;,$/\\<>|=&', RequireEachIncludedType=True)
    result["user2UserPassword"] = secrets_manager_response["RandomPassword"]    
    idp_client.admin_set_user_password(
        UserPoolId=globalConfig["UserPool"],
        Username=result["user2UserName"],
        Password=result["user2UserPassword"],
        Permanent=True
    )
    result["user2UserSub"] = idp_response["User"]["Username"]

    # get new user2 user authentication info
    idp_response = idp_client.initiate_auth(
        AuthFlow='USER_PASSWORD_AUTH',
        AuthParameters={
            'USERNAME': result["user2UserName"],
            'PASSWORD': result["user2UserPassword"]
        },
        ClientId=globalConfig["UserPoolClient"],
    )
    result["user2UserIdToken"] = idp_response["AuthenticationResult"]["IdToken"]
    result["user2UserAccessToken"] = idp_response["AuthenticationResult"]["AccessToken"]
    result["user2UserRefreshToken"] = idp_response["AuthenticationResult"]["RefreshToken"]
    return result

def clear_dynamo_tables():
    LOGGER.info("Clearing DynamoDb tables")
    # clear all data from the tables that will be used for testing
    dbd_client = boto3.client('dynamodb')
    db_response = dbd_client.scan(
        TableName=globalConfig['AddressTable'],
        AttributesToGet=['user_id', 'address_id']
    )
    for item in db_response["Items"]:
        dbd_client.delete_item(
            TableName=globalConfig['AddressTable'],
            Key={'user_id': {'S': item['user_id']["S"]}, 'address_id': {'S': item['address_id']["S"]}}
        )
    return

@pytest.fixture(scope='session')
def global_config(request):
    global globalConfig
    # load outputs of the stacks to test
    globalConfig.update(get_stack_outputs(APPLICATION_STACK_NAME))
    globalConfig.update(get_stack_outputs(MODULE4_STACK_NAME))
    globalConfig.update(create_cognito_accounts())
    clear_dynamo_tables()
    return globalConfig
