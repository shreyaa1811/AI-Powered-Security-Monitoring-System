import pandas as pd
import ipaddress

#Check the format of ip address

def safe_ip(ip) :
    try :
        return int(ipaddress.IPv4Address(ip))
    except :
        return 0

def preprocess(df) :
    #Timestamps
    df['timestamp'] = pd.to_datetime(df['timestamp'],errors='coerce')
    df['hour'] = df['timestamp'].dt.hour
    df['day'] = df['timestamp'].dt.day
    df['month'] = df['timestamp'].dt.month
    df['weekday'] = df['timestamp'].dt.weekday

    df.drop(columns=['timestamp'],inplace=True)

    #One hot encoding
    df = pd.get_dummies(df,columns=['event_type'])
    for col in df.select_dtypes('bool').columns:
        df[col] = df[col].astype(int)

    #IP conversion
    df['source_ip_int'] = df['source_ip'].apply(safe_ip)
    df.drop(columns=['source_ip'],inplace=True)

    return df