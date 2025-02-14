#%%
import streamlit as st
import pandas as pd
import time
import datetime
import xlsxwriter
from io import BytesIO
from PyPDF2 import PdfMerger
import zipfile
import pypdf
from PIL import Image
import json
import time
import smtplib
import mimetypes
import io
from email.message import EmailMessage
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from pprint import pprint
from email.utils import formataddr
import mimetypes
#%% function for page "เช็คว่าต้องจด VAT หรือยัง"
@st.cache_data(show_spinner = False)
def total_sale_shopee(shopee_file_ls, selected_year, store, is_full_year, current_month):
    #shopee uploaded files are in list
    df = pd.concat([pd.read_excel(f, converters = {'หมายเลขคำสั่งซื้อ': str}) for f in shopee_file_ls], axis = 0)
    
    if all(col in list(df.columns) for col in ['หมายเลขคำสั่งซื้อ', 'สถานะการสั่งซื้อ', 'วันที่ทำการสั่งซื้อ', 'ราคาขายสุทธิ', 'โค้ดส่วนลดชำระโดยผู้ขาย', 'ค่าจัดส่งที่ชำระโดยผู้ซื้อ']):
        df = df[~df['สถานะการสั่งซื้อ'].isin(['ยกเลิกแล้ว'])].drop_duplicates()
        df['year'] = pd.to_datetime(df['วันที่ทำการสั่งซื้อ'], format = '%Y-%m-%d %H:%M').dt.year #สำหรับตรวจว่า ปีของข้อมูลที่อัพโหลดมา ตรงกับปีที่เลือกไหม
        df['month'] = pd.to_datetime(df['วันที่ทำการสั่งซื้อ'], format = '%Y-%m-%d %H:%M').dt.month #สำหรับตรวจว่าข้อมูลครบทุกเดือน

        #check ว่าปีที่เลือก กับปีในไฟล์ตรงกัน
        if df[df['year'].astype(int) != int(selected_year)].shape[0] != 0 and df[df['year'].astype(int) == int(selected_year)].shape[0] == 0: 
            st.error(f'ข้อมูลร้านค้า {store} จาก Shopee: ปีที่เลือกคือปี {selected_year} / แต่มีแต่ข้อมูลของปี' + ', '.join(df['year'].astype(str).unique().tolist()) + '--> อาจเลือกไฟล์ผิด', icon="🚨")
            return None
        else:
            if df[df['year'].astype(int) != int(selected_year)].shape[0] != 0:
                st.warning(f'ข้อมูลร้านค้า {store} จาก Shopee มีข้อมูลของปี ' + ', '.join([y for y in df['year'].astype(str).unique().tolist() if y != selected_year]) +'ติดมาด้วย' + '--> กรุณาตรวจสอบ', icon="⚠️")
            
            #screen out year
            df = df[df['year'] == int(selected_year)]

            #check ว่าข้อมูลครบทุกเดือน
            ##################################################################################################
            # missing_month_ls = [m for m in [i for i in range(1, 13 if is_full_year else current_month + 1)] if m not in sorted(df['month'].unique().tolist())]

            if is_full_year: #get month_ls
                month_ls = [i for i in range(1, 13)]
            else: #not full year
                if current_month == 1:
                    month_ls = [1]
                else:
                    month_ls = [m for m in range(1, current_month)]
            missing_month_ls = [str(m) for m in month_ls if m not in df['month'].unique().tolist()]

            #เตือนว่าข้อมูไม่ครบ
            if missing_month_ls != []:
                st.warning(f'โปรดเช็คว่าการอัพโหลดไฟล์ถูกต้องหรือไม่: ไฟล์ยอดขายของร้าน {store} จาก Shopee ไม่มียอดขายในเดือนที่ {",".join(missing_month_ls)}', icon="⚠️")
            
            #screen out current month if current month != 1
            if current_month == 1 and selected_year == current_year: #จะเกิดกรณีเมื่อ เลือกปีนี้ และเดือนนี้คือเดือนที่ 1
                st.warning('เดือนนี้เดือน 1 แต่ยังไม่จบเดือน มีโอกาสที่สถานะคำสั่งซื้อจะยังเปลี่ยนแปลงเป็นยกเลิก', icon="ℹ️")

                date_ls = sorted(pd.date_range(start = f'1/1/{selected_year}', end = current_time.strftime('%d/%m/%Y'), freq= 'D'))
            else:
                if selected_year == current_year: #ไม่ใช่เดือน 1 แล้ว แต่กำลังดูข้อมูลปี ปจบ
                    st.info('เดือนนี้ยังไม่จบ โปรแกรมจะใช้ข้อมูลถึงแค่เดือนที่แล้วมาคำนวณ', icon="ℹ️")
                    df = df[df['month'] != current_month].reset_index(drop = True)
        
                    last_day_of_last_month = (current_time.replace(day = 1) - pd.Timedelta(days = 1)).strftime('%d/%m/%Y')
                    date_ls = sorted(pd.date_range(start = f'1/1/{selected_year}', end = last_day_of_last_month, freq = 'D'))

                else: #ข้อมูลเป็นของปีที่แล้ว
                    date_ls = sorted(pd.date_range(start = f'1/1/{selected_year}', end = f'31/12/{selected_year}', freq = 'D'))

            
            uncompleted_order_count = len(df[df['สถานะการสั่งซื้อ'] != 'สำเร็จแล้ว']['หมายเลขคำสั่งซื้อ'].unique().tolist())
            if uncompleted_order_count != 0:
                st.warning(f"ไฟล์ของร้าน {store} จาก Shopee  ยังมีคำสั่งซื้อที่ยังไม่สำเร็จอยู่ {uncompleted_order_count} รายการ --> อาจทำให้ค่ารายได้รวมเปลี่ยนแปลงได้หากมีการยกเลิกคำสั่งซื้อ", icon="⚠️")
            ##################################################################################################

            df['วันที่ทำการสั่งซื้อ'] = pd.to_datetime(df['วันที่ทำการสั่งซื้อ'], format = '%Y-%m-%d %H:%M').dt.date

            shopee_ls = []
            for date in date_ls:
                df1 = df[df['วันที่ทำการสั่งซื้อ'] == date.date()]

                if df1.shape[0] == 0:
                    shopee_ls.append([date.strftime('%Y-%m-%d'), None, None])
                else:
                    order_value = 0
                    shipping_value = 0

                    for order_id in df1['หมายเลขคำสั่งซื้อ'].unique():
                        df2 = df1[df1['หมายเลขคำสั่งซื้อ'] == order_id].reset_index(drop = True)
                        order_value += df2['ราคาขายสุทธิ'].sum() - float(df2['โค้ดส่วนลดชำระโดยผู้ขาย'].tolist()[0])
                        shipping_value += float(df2['ค่าจัดส่งที่ชำระโดยผู้ซื้อ'].tolist()[0])
                        
                    shopee_ls.append([date.strftime('%Y-%m-%d'), order_value, shipping_value])     

            shopee_result_df = pd.DataFrame(shopee_ls, columns = ['date', 'order_value', f'shipping_value']).fillna(0)
            shopee_result_df = shopee_result_df.set_index('date')
            shopee_result_df = shopee_result_df[['order_value', 'shipping_value']]
            shopee_result_df.columns = pd.MultiIndex.from_arrays([[store+'_shopee', store+'_shopee'], shopee_result_df.columns.tolist()])

            return shopee_result_df

    else:
        st.error(f'ข้อมูลที่อัพโหลดเป็นคนละ format กับที่โปรแกรมตั้งค่าเอาไว้ --> กรุณาเช็คความถูกต้อง', icon="🚨")
        return None

@st.cache_data(show_spinner = False)
def total_sale_lazada(lazada_file, selected_year, store, is_full_year, current_month):
    df = pd.read_excel(lazada_file, converters={'orderNumber':str})

    if all(col in list(df.columns) for col in ['status', 'orderNumber', 'createTime', 'paidPrice']):
        df = df[~df['status'].isin(['canceled', 'returned', 'Package Returned'])]

        df['year'] = pd.to_datetime(df['createTime'], format = '%d %b %Y %H:%M').dt.year #สำหรับตรวจว่า ปีของข้อมูลที่อัพโหลดมา ตรงกับปีที่เลือกไหม
        df['month'] = pd.to_datetime(df['createTime'], format = '%d %b %Y %H:%M').dt.month #สำหรับตรวจว่าข้อมูลครบทุกเดือน

        #check ว่าปีที่เลือก กับปีในไฟล์ตรงกัน
        if df[df['year'].astype(int) != int(selected_year)].shape[0] != 0 and df[df['year'].astype(int) == int(selected_year)].shape[0] == 0: 
            st.error(f'ข้อมูลร้านค้า {store} ของ Lazada: ปีที่เลือกคือปี {selected_year} / แต่มีแต่ข้อมูลของปี' + ', '.join(df['year'].astype(str).unique().tolist()) + '--> อาจเลือกไฟล์ผิด', icon="🚨")
            return None
        else:
            if df[df['year'].astype(int) != int(selected_year)].shape[0] != 0:
                st.warning(f'ข้อมูลร้านค้า {store} จาก Lazada มีข้อมูลของปี ' + ', '.join([y for y in df['year'].astype(str).unique().tolist() if y != selected_year]) +'ติดมาด้วย' + '--> กรุณาตรวจสอบ', icon="⚠️")

            #screen out year
            df = df[df['year'] == int(selected_year)]

            #check ว่าข้อมูลครบทุกเดือน
            ##################################################################################################
            # missing_month_ls = [m for m in [i for i in range(1, 13 if is_full_year else current_month + 1)] if m not in sorted(df['month'].unique().tolist())]

            if is_full_year: #get month_ls
                month_ls = [i for i in range(1, 13)]
            else: #not full year
                if current_month == 1:
                    month_ls = [1]
                else:
                    month_ls = [m for m in range(1, current_month)]
            missing_month_ls = [str(m) for m in month_ls if m not in df['month'].unique().tolist()]

            #เตือนว่าข้อมูไม่ครบ
            if missing_month_ls != []:
                st.warning(f'โปรดเช็คว่าการอัพโหลดไฟล์ถูกต้องหรือไม่: ไฟล์ยอดขายของร้าน {store} จาก Lazada ไม่มียอดขายในเดือนที่ {",".join(missing_month_ls)}', icon="⚠️")
            
            #screen out current month if current month != 1
            if current_month == 1 and selected_year == current_year: #จะเกิดกรณีเมื่อ เลือกปีนี้ และเดือนนี้คือเดือนที่ 1
                st.warning('เดือนนี้เดือน 1 แต่ยังไม่จบเดือน มีโอกาสที่สถานะคำสั่งซื้อจะยังเปลี่ยนแปลงอยู่นะ', icon="ℹ️")

                date_ls = sorted(pd.date_range(start = f'1/1/{selected_year}', end = current_time.strftime('%d/%m/%Y'), freq= 'D'))
            else:
                if selected_year == current_year: #ไม่ใช่เดือน 1 แล้ว แต่กำลังดูข้อมูลปี ปจบ
                    st.info('เดือนนี้ยังไม่จบ ใช้ข้อมูลถึงแค่เดือนที่แล้วมาคำนวณ', icon="ℹ️")
                    df = df[df['month'] != current_month].reset_index(drop = True)
                    
                    last_day_of_last_month = (current_time.replace(day = 1) - pd.Timedelta(days = 1)).strftime('%d/%m/%Y')
                    date_ls = sorted(pd.date_range(start = f'1/1/{selected_year}', end = last_day_of_last_month, freq = 'D'))
                else: #ข้อมูลเป็นของปีที่แล้ว
                    date_ls = sorted(pd.date_range(start = f'1/1/{selected_year}', end = f'31/12/{selected_year}', freq = 'D'))
            
            uncompleted_order_count = len(df[df['status'] != 'confirmed']['status'].unique().tolist())
            if uncompleted_order_count != 0:
                st.warning(f"ไฟล์ของร้าน {store} จาก Lazada ยังมีคำสั่งซื้อที่ยังไม่สำเร็จอยู่ {uncompleted_order_count} รายการ --> อาจทำให้ค่ารายได้รวมเปลี่ยนแปลงได้หากมีการยกเลิกคำสั่งซื้อ", icon="⚠️")
                # st.dataframe(df[df['status'] != 'confirmed'])
            ##################################################################################################

            df['createTime'] = pd.to_datetime(df['createTime'], format = '%d %b %Y %H:%M').dt.date

            lazada_ls = []
            for date in date_ls:
                df1 = df[df['createTime'] == date.date()]

                if df1.shape[0] == 0:
                    lazada_ls.append([date.strftime('%Y-%m-%d'), None, None])
                else:
                    order_value = df1['paidPrice'].sum()
                    shipping_value = None
                    lazada_ls.append([date.strftime('%Y-%m-%d'), order_value, shipping_value])

            lazada_result_df = pd.DataFrame(lazada_ls, columns = ['date', 'order_value', 'shipping_value']).fillna(0)
            lazada_result_df = lazada_result_df.set_index('date')
            lazada_result_df = lazada_result_df[['order_value', 'shipping_value']]
            lazada_result_df.columns = pd.MultiIndex.from_arrays([[store+'_lazada', store+'_lazada'], lazada_result_df.columns.tolist()])

            return lazada_result_df
    else:
        st.error(f'ข้อมูลที่อัพโหลดเป็นคนละ format กับที่โปรแกรมตั้งค่าเอาไว้ --> กรุณาเช็คความถูกต้อง', icon="🚨")
        return None

# def total_sale_lazada(lazada_file, selected_year, store, is_full_year, current_month):
@st.cache_data(show_spinner = False)
def total_sale_tiktok(tiktok_file, selected_year, store, is_full_year, current_month):
    # st.write(tiktok_file)
    df = pd.read_csv(tiktok_file, converters={'Order ID':str})
    # st.write(df.columns)

    if all(col in list(df.columns) for col in ['Order ID', 'Order Status', 'Created Time', 'SKU Subtotal Before Discount', 'Shipping Fee After Discount', 'SKU Seller Discount']):
        df = df[df['Order Status'] != 'Canceled'].drop_duplicates().reset_index(drop = True)

        df['year'] = pd.to_datetime(df['Created Time'], format = '%d/%m/%Y %H:%M:%S\t').dt.year #สำหรับตรวจว่า ปีของข้อมูลที่อัพโหลดมา ตรงกับปีที่เลือกไหม
        df['month'] = pd.to_datetime(df['Created Time'], format = '%d/%m/%Y %H:%M:%S\t').dt.month #สำหรับตรวจว่าข้อมูลครบทุกเดือน

        #check ว่าปีที่เลือก กับปีในไฟล์ตรงกัน
        if df[df['year'].astype(int) != int(selected_year)].shape[0] != 0 and df[df['year'].astype(int) == int(selected_year)].shape[0] == 0: 
            st.error(f'ข้อมูลร้านค้า {store} จาก TikTok: ปีที่เลือกคือปี {selected_year} / แต่มีแต่ข้อมูลของปี' + ', '.join(df['year'].astype(str).unique().tolist()) + '--> อาจเลือกไฟล์ผิด', icon="🚨")
            return None
        else:
            if df[df['year'].astype(int) != int(selected_year)].shape[0] != 0:
                st.warning(f'ข้อมูลร้านค้า {store} จาก TikTok มีข้อมูลของปี ' + ', '.join([y for y in df['year'].astype(str).unique().tolist() if y != selected_year]) +'ติดมาด้วย' + '--> กรุณาตรวจสอบ', icon="⚠️")
            
            #screen out year
            df = df[df['year'] == int(selected_year)]

            #check ว่าข้อมูลครบทุกเดือน
            ##################################################################################################
            missing_month_ls = [m for m in [i for i in range(1, 13 if is_full_year else current_month + 1)] if m not in sorted(df['month'].unique().tolist())]

            if is_full_year: #get month_ls
                month_ls = [i for i in range(1, 13)]
            else: #not full year
                if current_month == 1:
                    month_ls = [1]
                else:
                    month_ls = [m for m in range(1, current_month)]
            missing_month_ls = [str(m) for m in month_ls if m not in df['month'].unique().tolist()]

            #เตือนว่าข้อมูลไม่ครบ
            if missing_month_ls != []:
                st.warning(f'โปรดเช็คว่าการอัพโหลดไฟล์ถูกต้องหรือไม่: ไฟล์ยอดขายของร้าน {store} จาก TikTok ไม่มียอดขายในเดือนที่ {", ".join(missing_month_ls)}', icon="⚠️")
                return None
            #screen out current month if current month != 1
            if current_month == 1 and selected_year == current_year: #จะเกิดกรณีเมื่อ เลือกปีนี้ และเดือนนี้คือเดือนที่ 1
                st.warning('เดือนนี้เดือน 1 แต่ยังไม่จบเดือน มีโอกาสที่สถานะคำสั่งซื้อจะยังเปลี่ยนแปลงอยู่นะ', icon="ℹ️")

                date_ls = sorted(pd.date_range(start = f'1/1/{selected_year}', end = current_time.strftime('%d/%m/%Y'), freq= 'D'))
                # st.write(date_ls)
            else:
                if selected_year == current_year: #ไม่ใช่เดือน 1 แล้ว แต่กำลังดูข้อมูลปี ปจบ
                    st.info('เดือนนี้ยังไม่จบ ใช้ข้อมูลถึงแค่เดือนที่แล้วมาคำนวณ', icon="ℹ️")
                    df = df[df['month'] != current_month].reset_index(drop = True)
                    
                    last_day_of_last_month = (current_time.replace(day = 1) - pd.Timedelta(days = 1)).strftime('%d/%m/%Y')
                    date_ls = sorted(pd.date_range(start = f'1/1/{selected_year}', end = last_day_of_last_month, freq = 'D'))
                else: #ข้อมูลเป็นของปีที่แล้ว
                    date_ls = sorted(pd.date_range(start = f'1/1/{selected_year}', end = f'31/12/{selected_year}', freq = 'D'))
            
            uncompleted_order_count = len(df[df['Order Status'] != 'Completed']['Order Status'].unique().tolist())
            if uncompleted_order_count != 0:
                st.warning(f"ไฟล์ของร้าน {store} จาก TikTok ยังมีคำสั่งซื้อที่ยังไม่สำเร็จอยู่ {uncompleted_order_count} รายการ --> อาจทำให้ค่ารายได้รวมเปลี่ยนแปลงได้หากมีการยกเลิกคำสั่งซื้อ", icon="⚠️")
                ##########

            df['Created Time'] = pd.to_datetime(df['Created Time'], format = '%d/%m/%Y %H:%M:%S\t').dt.date

            tiktok_ls = []
            for date in date_ls:
                df1 = df[df['Created Time'] == date.date()]

                if df1.shape[0] == 0:
                    tiktok_ls.append([date.strftime('%Y-%m-%d'), None, None])
                else:
                    order_value = 0
                    shipping_value = 0

                    for order_id in df1['Order ID'].unique():
                        df2 = df1[df1['Order ID'] == order_id].reset_index(drop = True)

                        order_value += df2['SKU Subtotal Before Discount'].str.replace('THB ', '').str.replace(',', '').astype(float).sum() - float(df2['SKU Seller Discount'].str.replace('THB ', '').str.replace(',', '').astype(float).sum())
                        shipping_value += float(df2.loc[0, 'Shipping Fee After Discount'].replace('THB ', '').replace(',', ''))
                        
                    tiktok_ls.append([date.strftime('%Y-%m-%d'), order_value, shipping_value])
                
            tiktok_result_df = pd.DataFrame(tiktok_ls, columns = ['date', 'order_value', 'shipping_value']).fillna(0)
            tiktok_result_df = tiktok_result_df.set_index('date')
            tiktok_result_df = tiktok_result_df[['order_value', 'shipping_value']]
            tiktok_result_df.columns = pd.MultiIndex.from_arrays([[store+'_tiktok', store+'_tiktok'], tiktok_result_df.columns.tolist()])

            return tiktok_result_df
    else:
        st.error(f'ข้อมูลที่อัพโหลดเป็นคนละ format กับที่โปรแกรมตั้งค่าเอาไว้ --> กรุณาเช็คความถูกต้อง', icon="🚨")
        # print('aaa')
        return None

#%% function for page 'คำนวณ vat'
@st.cache_data(show_spinner=False)
def vat_cal_sale_shopee(shopee_sale_file, year, store, month):
    df = pd.read_excel(shopee_sale_file, converters={'หมายเลขคำสั่งซื้อ':str})
    df = df[~df['สถานะการสั่งซื้อ'].isin(['ยกเลิกแล้ว'])].drop_duplicates()

    df['year'] = pd.to_datetime(df['วันที่ทำการสั่งซื้อ'], format = '%Y-%m-%d %H:%M').dt.year #สำหรับตรวจว่า ปีของข้อมูลที่อัพโหลดมา ตรงกับปีที่เลือกไหม
    df['month'] = pd.to_datetime(df['วันที่ทำการสั่งซื้อ'], format = '%Y-%m-%d %H:%M').dt.month #สำหรับตรวจว่าข้อมูลครบทุกเดือน

    #check ว่าปีที่เลือก กับปีในไฟล์ตรงกัน
    if df[df['year'].astype(int) != int(year)].shape[0] != 0 and df[df['year'].astype(int) == int(year)].shape[0] == 0: 
        st.error(f'ข้อมูลร้านค้า {store} จาก Shopee: ปีที่เลือกคือเดือน {month}/{year} แต่ไม่มีข้อมูลของเดือนนี้' + '--> อาจเลือกไฟล์ผิด', icon="🚨")
        # st.dataframe(df)
        return None
    
    else:
        if df[(df['year'].astype(int) != int(year)) & (df['month'].astype(int) != int(month))].shape[0] != 0:
            st.warning(f'ข้อมูลร้านค้า {store} จาก Shopee: ปีที่เลือกคือเดือน {month}/{year} มีข้อมูลของเดือนอื่นติดมาด้วย' + '--> กรุณาตรวจสอบ', icon="⚠️")

        #screen out year
        df = df[(df['year'] == int(year)) & (df['month'] == month)].reset_index(drop = True)

        uncompleted_order_count = len(df[df['สถานะการสั่งซื้อ'] != 'สำเร็จแล้ว']['หมายเลขคำสั่งซื้อ'].unique().tolist())
        if uncompleted_order_count != 0:
            st.warning(f"ไฟล์ของร้าน {store} (Shopee) ยังมีคำสั่งซื้อที่ยังไม่สำเร็จอยู่ {uncompleted_order_count} รายการ --> อาจทำให้ค่ารายได้รวมเปลี่ยนแปลงได้หากมีการยกเลิกคำสั่งซื้อ", icon="⚠️")

        df['วันที่ทำการสั่งซื้อ'] = pd.to_datetime(df['วันที่ทำการสั่งซื้อ'], format = '%Y-%m-%d %H:%M').dt.date
        # shopee_sale_df['หมายเลขคำสั่งซื้อ'] = shopee_sale_df['หมายเลขคำสั่งซื้อ'].astype(str)
        df = df[['สถานะการสั่งซื้อ', 'วันที่ทำการสั่งซื้อ', 'หมายเลขคำสั่งซื้อ', 'ชื่อผู้ใช้ (ผู้ซื้อ)', 'ราคาขายสุทธิ', 'โค้ดส่วนลดชำระโดยผู้ขาย', 'ค่าจัดส่งที่ชำระโดยผู้ซื้อ', 'ค่าจัดส่งที่ Shopee ออกให้โดยประมาณ', 'ค่าจัดส่งสินค้าคืน', 'ค่าจัดส่งโดยประมาณ']]

        sale_ls = []
        for order_id in df['หมายเลขคำสั่งซื้อ'].unique():
            df1 = df[df['หมายเลขคำสั่งซื้อ'] == order_id].reset_index(drop = True)
            order_date = df1.loc[0, 'วันที่ทำการสั่งซื้อ']
            order_no = df1.loc[0, 'หมายเลขคำสั่งซื้อ']
            customer_name = df1.loc[0, 'ชื่อผู้ใช้ (ผู้ซื้อ)']
            seller_discount_code = float(df1.loc[0, 'โค้ดส่วนลดชำระโดยผู้ขาย'])
            include_vat = df1['ราคาขายสุทธิ'].sum() - seller_discount_code
            vat = round((include_vat * 0.07) / 1.07, 2)
            before_vat = include_vat - vat
            status = df1.loc[0, 'สถานะการสั่งซื้อ']

            sale_ls.append(['Shopee', store, 'สินค้า', order_date, status, order_no, customer_name, before_vat, vat, include_vat])

            shipping_fee_from_buyer = df1.loc[0, 'ค่าจัดส่งที่ชำระโดยผู้ซื้อ']
            if float(shipping_fee_from_buyer) != 0:
                shipping_vat = round((shipping_fee_from_buyer * 0.07) / 1.07, 2)
                shipping_before_vat = shipping_fee_from_buyer - shipping_vat
                sale_ls.append(['Shopee', store, 'บริการ', order_date, status, order_no, customer_name, shipping_before_vat, shipping_vat, shipping_fee_from_buyer])

        shopee_sale_df_result = pd.DataFrame(sale_ls, columns = ['platform', 'store_name', 'type', 'order_date', 'status', 'order_no', 'customer_name', 'before_vat', 'vat', 'include_vat'])
        shopee_sale_df_result = shopee_sale_df_result[['platform', 'store_name', 'type', 'order_date', 'status', 'order_no', 'customer_name', 'before_vat', 'vat', 'include_vat']]

    return shopee_sale_df_result
    
@st.cache_data(show_spinner=False)
def vat_cal_sale_lazada(lazada_sale_file, year, store, month):
    df = pd.read_excel(lazada_sale_file, converters={'orderNumber':str})
    df = df[~df['status'].isin(['canceled', 'returned', 'Package Returned'])].drop_duplicates().reset_index(drop = True)

    df['year'] = pd.to_datetime(df['createTime'], format = '%d %b %Y %H:%M').dt.year #สำหรับตรวจว่า ปีของข้อมูลที่อัพโหลดมา ตรงกับปีที่เลือกไหม
    df['month'] = pd.to_datetime(df['createTime'], format = '%d %b %Y %H:%M').dt.month #สำหรับตรวจว่าข้อมูลครบทุกเดือน

    #check ว่าปีที่เลือก กับปีในไฟล์ตรงกัน
    if df[df['year'].astype(int) != int(year)].shape[0] != 0 and df[df['year'].astype(int) == int(year)].shape[0] == 0: 
        st.error(f'ข้อมูลร้านค้า {store} จาก Lazada: ปีที่เลือกคือปี {year} / แต่มีแต่ข้อมูลของปี' + ', '.join(df['year'].astype(str).unique().tolist()) + '--> อาจเลือกไฟล์ผิด', icon="🚨")
        # st.dataframe(df)
        return None
    else:
        if df[(df['year'].astype(int) != int(year)) & (df['month'].astype(int) != int(month))].shape[0] != 0:
            st.warning(f'ข้อมูลร้านค้า {store} จาก Lazada: ปีที่เลือกคือเดือน {month}/{year} มีข้อมูลของเดือนอื่นติดมาด้วย' + '--> กรุณาตรวจสอบ', icon="⚠️")

        #screen out year
        df = df[(df['year'] == int(year)) & (df['month'] == month)].reset_index(drop = True)

        uncompleted_order_count = len(df[df['status'] != 'confirmed']['status'].unique().tolist())
        if uncompleted_order_count != 0:
            st.warning(f"ไฟล์ของร้าน {store} (Lazada) ยังมีคำสั่งซื้อที่ยังไม่สำเร็จอยู่ {uncompleted_order_count} รายการ --> อาจทำให้ค่ารายได้รวมเปลี่ยนแปลงได้หากมีการยกเลิกคำสั่งซื้อ", icon="⚠️")
            # st.dataframe(df[df['status'] != 'confirmed'])
        ##################################################################################################

    df['createTime'] = pd.to_datetime(df['createTime'], format = '%d %b %Y %H:%M').dt.date
    df = df[['status', 'createTime', 'orderNumber', 'customerName', 'paidPrice', 'sellerDiscountTotal']]

    sale_ls = []
    for order_id in df['orderNumber'].unique():
        df1 = df[df['orderNumber'] == order_id].reset_index(drop = True)

        order_date = df1.loc[0, 'createTime']
        order_no = str(df1.loc[0, 'orderNumber'])
        customer_name = df1.loc[0, 'customerName']
        include_vat = df1['paidPrice'].sum()
        vat = round((include_vat * 0.07) / 1.07, 2)
        before_vat = include_vat - vat

        status = df1.loc[0, 'status']

        sale_ls.append(['Lazada', store, 'สินค้า', order_date, status, order_no, customer_name, before_vat, vat, include_vat])

    lazada_sale_df_result = pd.DataFrame(sale_ls, columns = ['platform', 'store_name', 'type', 'order_date', 'status', 'order_no', 'customer_name', 'before_vat', 'vat', 'include_vat'])
    lazada_sale_df_result = lazada_sale_df_result[['platform', 'store_name', 'type', 'order_date', 'status', 'order_no', 'customer_name', 'before_vat', 'vat', 'include_vat']]

    return lazada_sale_df_result

@st.cache_data(show_spinner=False)
def vat_cal_sale_tiktok(tiktok_sale_file, year, store, month):
    df = pd.read_csv(tiktok_sale_file, converters={'Order ID':str})
    df = df[~df['Order Status'].isin(['Canceled'])]
    df = df[df['Order Status'] != 'Canceled'].drop_duplicates().reset_index(drop = True)

    df['year'] = pd.to_datetime(df['Created Time'], format = '%d/%m/%Y %H:%M:%S\t').dt.year #สำหรับตรวจว่า ปีของข้อมูลที่อัพโหลดมา ตรงกับปีที่เลือกไหม
    df['month'] = pd.to_datetime(df['Created Time'], format = '%d/%m/%Y %H:%M:%S\t').dt.month #สำหรับตรวจว่าข้อมูลครบทุกเดือน

    #check ว่าปีที่เลือก กับปีในไฟล์ตรงกัน
    if df[df['year'].astype(int) != int(year)].shape[0] != 0 and df[df['year'].astype(int) == int(year)].shape[0] == 0: 
        st.error(f'ข้อมูลร้านค้า {store} | TikTok: ปีที่เลือกคือปี {year} / แต่มีแต่ข้อมูลของปี' + ', '.join(df['year'].astype(str).unique().tolist()) + '--> อาจเลือกไฟล์ผิด', icon="🚨")
        return None
    else:
        if df[(df['year'].astype(int) != int(year)) & (df['month'].astype(int) != int(month))].shape[0] != 0:
            st.warning(f'ข้อมูลร้านค้า {store} | TikTok: ปีที่เลือกคือเดือน {month}/{year} มีข้อมูลของเดือนอื่นติดมาด้วย' + '--> กรุณาตรวจสอบ', icon="⚠️")

        #screen out year
        df = df[(df['year'] == int(year)) & (df['month'] == month)].reset_index(drop = True)

        uncompleted_order_count = len(df[df['Order Status'] != 'Completed']['Order Status'].unique().tolist())
        if uncompleted_order_count != 0:
            st.warning(f"ไฟล์ของร้าน {store} (TikTok) ยังมีคำสั่งซื้อที่ยังไม่สำเร็จอยู่ {uncompleted_order_count} รายการ --> อาจทำให้ค่ารายได้รวมเปลี่ยนแปลงได้หากมีการยกเลิกคำสั่งซื้อ", icon="⚠️")
            ##########

    df['SKU Subtotal Before Discount'] = df['SKU Subtotal Before Discount'].str.replace('THB ', '').str.replace(',', '').astype(float)
    df['SKU Seller Discount'] = df['SKU Seller Discount'].str.replace('THB ', '').str.replace(',', '').astype(float)
    df['Shipping Fee After Discount'] = df['Shipping Fee After Discount'].str.replace('THB ', '').str.replace(',', '').astype(float)
    df = df[['Order Status', 'Created Time', 'Order ID', 'Buyer Username', 'SKU Subtotal Before Discount', 'SKU Seller Discount',
                                    'Shipping Fee After Discount']]

    sale_ls = []
    for order_id in df['Order ID'].unique():
        df1 = df[df['Order ID'] == order_id].reset_index(drop = True)

        order_date = df1.loc[0, 'Created Time']
        order_no = str(df1.loc[0, 'Order ID']).replace('\t', '')
        customer_name = df1.loc[0, 'Buyer Username']
        seller_discount_code = float(df1['SKU Seller Discount'].sum())
        include_vat = df1['SKU Subtotal Before Discount'].sum() - seller_discount_code
        vat = round((include_vat * 0.07) / 1.07, 2)
        before_vat = include_vat - vat

        status = df1.loc[0, 'Order Status']

        sale_ls.append(['TikTok', store, 'สินค้า', order_date, status, order_no, customer_name, before_vat, vat, include_vat])

        shipping_fee_from_buyer = df1.loc[0, 'Shipping Fee After Discount']

        if float(shipping_fee_from_buyer) != 0:
            shipping_vat = round((shipping_fee_from_buyer * 0.07) / 1.07, 2)
            shipping_before_vat = shipping_fee_from_buyer - shipping_vat
            sale_ls.append(['TikTok', store, 'บริการ', order_date, status, order_no, customer_name, shipping_before_vat, shipping_vat, shipping_fee_from_buyer])


    tiktok_sale_df_result = pd.DataFrame(sale_ls, columns = ['platform', 'store_name', 'type', 'order_date', 'status', 'order_no', 'customer_name', 'before_vat', 'vat', 'include_vat'])
    tiktok_sale_df_result = tiktok_sale_df_result[['platform', 'store_name', 'type', 'order_date', 'status', 'order_no', 'customer_name', 'before_vat', 'vat', 'include_vat']]

    return tiktok_sale_df_result  

@st.cache_data(show_spinner=False)
def vat_cal_commission_shopee(store_name, shopee_zip_file, month, year):
    commission_ls = []
    pdf_ls = []
    doc_date_not_in_target_month_count = 0

    progress_bar = st.progress(0, text = 'processing shopee commission pdf')
    with zipfile.ZipFile(shopee_zip_file, 'r') as z:
        sorted_file_ls = ['-'.join(ls) for ls in sorted([n.split('-') for n in z.namelist() if 'SPX' not in n], key = lambda x: int(x[4]))]
        
                            
        for i, file_name in enumerate(sorted_file_ls):
            if 'SPX' in file_name:
                progress_bar.progress((i + 1) / len(sorted_file_ls), text = 'reading shopee commission pdf files')
            else:
                pdf_file = pypdf.PdfReader(BytesIO(z.read(file_name)))
                doc_date, doc_num, issued_company, before_vat, vat, company_name, company_tax_id = None, None, None, None, None, None, None

                for j, text in enumerate(pdf_file.pages[0].extract_text().split('\n')):
                    if 'วันที่' in text and 'ภายในวันที่' not in text:
                        doc_date = pd.to_datetime(text.split(' ')[-1], format = '%d/%m/%Y').date()
                    elif 'Co.,' in text:
                        issued_company = text
                    elif 'เลขที่' in text:
                        doc_num = text.split('No. ')[-1] + ' ' + pdf_file.pages[0].extract_text().split('\n')[j + 1]
                        if 'เลขประจำตัวผู้เสียภาษี' in text:
                            company_tax_id = text.split('Tax ID ')[1].split('เลขที่/')[0]
                    elif 'เลขประจำตัวผู้เสียภาษี' in text:
                        company_tax_id = text.split('Tax ID ')[1].split('เลขที่/')[0]
                    elif 'after discount' in text:
                        before_vat = round(float(text.split(' ')[-1].replace(',', '')), 2)
                    elif 'VAT' in text and '7%' in text:
                        vat = round(float(text.split(' ')[-1].replace(',', '')), 2)
                    elif 'Customer name' in text:
                        company_name = text.split('Customer name ')[-1]
                                
            if None in [doc_date, company_name, company_tax_id, issued_company, doc_num, before_vat, vat]:
                st.error(f'format file ใบเสร็จค่าธรรมเนียมของ Shopee ร้าน {store_name} (ไฟล์: {file_name}) อยู่ใน format ที่โปรแกรมไม่รองรับ กรุณาติดต่อ page vat_cal', icon="🚨")
                return None
            else:
                if doc_date.month == month and doc_date.year == year:
                    commission_ls.append([store_name, 'Shopee', doc_date, company_name, company_tax_id, issued_company, doc_num, before_vat, vat])
                    pdf_ls.append([company_name, 'Shopee', company_tax_id, doc_date, BytesIO(z.read(file_name)), store_name])
                    progress_bar.progress((i + 1) / len(sorted_file_ls), text = f'reading {store} Shopee commission files')
                else:
                    doc_date_not_in_target_month_count += 1
                    progress_bar.progress((i + 1) / len(sorted_file_ls), text = f'reading {store} Shopee commission files')

    if doc_date_not_in_target_month_count != 0:
        st.warning(f'มีไฟล์ใบเสร็จค่าธรรมเนียมของ Shopee {doc_date_not_in_target_month_count} ไฟล์ ที่ไม่ออกในเดือน {month} กรุณาตรวจเช็คความถูกต้อง', icon = '⚠️')

    progress_bar.empty()

    return  {
        'commission_df': pd.DataFrame(commission_ls, columns = ['store_name', 'platform', 'doc_date', 'company_name', 'company_tax_id', 'issue_comapny', 'doc_num', 'before_vat', 'vat']), 
        'pdf_df': pd.DataFrame(pdf_ls, columns = ['company_name', 'platform', 'company_tax_id', 'doc_date', 'pdf_file', 'store_name'])
        }

@st.cache_data(show_spinner=False)
def vat_cal_commission_lazada(store_name, lazada_file_ls, month, year):
    ls = []
    pdf_ls = []
    doc_num_ls = []
    doc_date_not_in_target_month_count = 0

    progress_bar = st.progress(0, text = 'processing Lazada commission pdf')
    for file_order, file_name in enumerate(lazada_file_ls):
        pdf_file = pypdf.PdfReader(file_name)

        if 'Lazada Express Limited' in pdf_file.pages[0].extract_text() or 'Shipping Fee' in pdf_file.pages[0].extract_text():
            progress_bar.progress((file_order + 1) / len(lazada_file_ls), text = 'reading Lazada commission pdf files')
        
        else: 
            doc_date, doc_num, issued_company, before_vat, vat, company_name, company_tax_id = None, None, None, None, None, None, None

            #มีคำว่า 'TAX INVOICE / RECEIPT'
            if 'TAX INVOICE / RECEIPT' in pdf_file.pages[0].extract_text():
                # st.write(pdf_file.pages[0].extract_text().split('\n'))
                for j, text in enumerate(pdf_file.pages[0].extract_text().split('\n')):
                    if 'Invoice Date' in text:
                        doc_date = pd.to_datetime(text.split(': ')[-1], format = '%Y-%m-%d').date()
                    elif 'Lazada' in text:
                        issued_company = text
                    elif 'Total' in text and '(Including Tax)' not in text:
                        before_vat = float(text.split(' ')[-1].replace(',', ''))
                    elif '7% (VAT)' in text:
                        vat = float(text.split(') ')[-1].replace(',', ''))
                    elif 'Invoice No.:' in text:
                        doc_num = text.split(' ')[-1]
                    elif 'TAX INVOICE / RECEIPT' in text:
                        company_name = pdf_file.pages[0].extract_text().split('\n')[j + 2]
                        company_tax_id = pdf_file.pages[0].extract_text().split('\n')[j + 7].split('Tax ID: ')[-1].split('Invoice')[0]
            
            #กรณีอื่น --> ตอนนี้ที่เจอคือ ใบคืนเงิน
            elif 'CREDIT NOTE' in pdf_file.pages[0].extract_text() and 'Reversal Commission' in pdf_file.pages[0].extract_text():
                # st.write(pdf_file.pages[0].extract_text().split('\n'))
                for j, text in enumerate(pdf_file.pages[0].extract_text().split('\n')):
                    if 'Date: ' in text:
                        doc_date = pd.to_datetime(text.split(': ')[-1], format = '%Y-%m-%d').date()
                    elif 'Lazada' in text:
                        issued_company = text
                    elif 'Total' in text and '(Including Tax)' not in text:
                        before_vat = float(text.split(' ')[-1].replace(',', '')) * -1
                    elif '7% (VAT)' in text:
                        vat = float(text.split(') ')[-1].replace(',', '')) * -1
                    elif 'CREDIT NOTE' in text:
                        company_name = pdf_file.pages[0].extract_text().split('\n')[j + 2].replace('  ', ' ')
                        company_tax_id = pdf_file.pages[0].extract_text().split('\n')[j + 7].split('Tax ID: ')[-1].split('Credit Note')[0]
                    elif 'Credit Note: ' in text:
                        doc_num = text.split('Credit Note: ')[-1]
                    
            if None in [doc_date, company_name, company_tax_id, issued_company, doc_num, before_vat, vat]:
                st.error(f'format file ใบเสร็จค่าธรรมเนียมของ Lazada ร้าน {store_name} (ไฟล์: {file_name}) อยู่ใน format ที่โปรแกรมไม่รองรับ กรุณาติดต่อ page vat_cal', icon="🚨")
                return None
            elif doc_num in doc_num_ls: #ไฟล์ที่อ่าน มีเลขเอกสารซ้ำ น่าจะเพราะอัพโหลดมาซ้ำ
                progress_bar.progress((file_order + 1) / len(lazada_file_ls), text = 'reading Lazada commission pdf files')
            else:
                if doc_date.month == month and doc_date.year == year:
                    ls.append([store_name, 'Lazada', doc_date, company_name, company_tax_id, issued_company, doc_num, before_vat, vat])
                    pdf_ls.append([company_name, 'Lazada', company_tax_id, doc_date, file_name, store_name])
                    doc_num_ls.append(doc_num) #เอามากัน กรณีคนอัพโหลดไฟล์มาซ้ำ
                    progress_bar.progress((i + 1) / len(lazada_file_ls), text = f'reading {store_name} Lazada commission files')
                else:
                    doc_date_not_in_target_month_count += 1
                    progress_bar.progress((i + 1) / len(lazada_file_ls), text = f'reading {store_name} Lazada commission files')
                

    if doc_date_not_in_target_month_count != 0:
        st.warning(f'มีไฟล์ใบเสร็จค่าธรรมเนียมของ Lazada {doc_date_not_in_target_month_count} ไฟล์ ที่ไม่ออกในเดือน {month} กรุณาตรวจเช็คความถูกต้อง', icon = '⚠️')

    progress_bar.empty()

    return {
        'commission_df': pd.DataFrame(ls, columns = ['store_name', 'platform', 'doc_date', 'company_name', 'company_tax_id', 'issue_comapny', 'doc_num', 'before_vat', 'vat']), 
        'pdf_df': pd.DataFrame(pdf_ls, columns = ['company_name', 'platform', 'company_tax_id', 'doc_date', 'pdf_file', 'store_name'])
    }

st.cache_data(show_spinner = False)
def vat_cal_commission_tiktok(store_name, tiktok_zip_file, month, year):
    ls = []
    pdf_ls = []
    doc_date_not_in_target_month_count = 0

    progress_bar = st.progress(0, text = 'processing TikTok commission pdf')
    with zipfile.ZipFile(tiktok_zip_file,'r') as z:
        sorted_file_ls = sorted([n for n in z.namelist() if 'THJV' not in n and 'TTSTHAC' not in n])

        for i, file_name in enumerate(sorted_file_ls):
            if 'THJV' in file_name or 'TTSTHAC' in file_name:
                progress_bar.progress((i + 1) / len(sorted_file_ls), text='reading tiktok commission pdf files')
            else:
                # pdf_file = pypdf.PdfReader(BytesIO(z.read(file_name)))
                pdf_file = pypdf.PdfReader(BytesIO(z.read(file_name)))
                doc_date, doc_num, issued_company, before_vat, vat, company_name, company_tax_id = None, None, None, None, None, None, None
                for j, text in enumerate(pdf_file.pages[0].extract_text().split('\n')):
                    if 'Invoice date' in text:
                        doc_date = pd.to_datetime(text.split(' : ')[-1], format = '%b %d, %Y').date()
                    elif 'Ltd.' in text and 'prepared by' not in text and 'For corporate' not in text:
                        issued_company = text
                    elif 'Invoice number : ' in text:
                        doc_num = text.split('Invoice number : ')[-1]
                    elif 'Subtotal (excluding VAT)' in text:
                        before_vat = float(text.split(' ')[-1].replace(',', '').replace('฿', ''))
                    elif 'Total VAT' in text and '7%' in text:
                        vat = float(text.split(' ')[-1].replace(',', '').replace('฿', '')) 
                    elif 'Client Name' in text:
                        company_name = text.split('Client Name: ')[-1]
                    elif 'Tax ID:' in text:
                        company_tax_id = text.split(': ')[-1]

                if None in [doc_date, company_name, company_tax_id, issued_company, doc_num, before_vat, vat]:
                    st.error(f'format file ใบเสร็จค่าธรรมเนียมของ TikTok ร้าน {store_name} (ไฟล์: {file_name}) อยู่ใน format ที่โปรแกรมไม่รองรับ กรุณาติดต่อ page vat_cal', icon="🚨")
                    return None
                else:
                    if doc_date.month == month and doc_date.year == year:
                        ls.append([store_name, 'TikTok', doc_date, company_name, company_tax_id, issued_company, doc_num, before_vat, vat])
                        pdf_ls.append([company_name, 'TikTok', company_tax_id, doc_date, BytesIO(z.read(file_name)), store_name])
                        progress_bar.progress((i + 1) / len(sorted_file_ls), text = f'reading {store} Shopee commission files')
                    else:
                        doc_date_not_in_target_month_count += 1
                
        if doc_date_not_in_target_month_count != 0:
            st.warning(f'มีไฟล์ใบเสร็จค่าธรรมเนียมของ TikTok {doc_date_not_in_target_month_count} ไฟล์ ที่ไม่ออกในเดือน {month} กรุณาตรวจเช็คความถูกต้อง', icon = '⚠️')
    
        progress_bar.empty()

    return {
            'commission_df': pd.DataFrame(ls, columns = ['store_name', 'platform', 'doc_date', 'company_name', 'company_tax_id', 'issue_comapny', 'doc_num', 'before_vat', 'vat']), 
            'pdf_df': pd.DataFrame(pdf_ls, columns = ['company_name', 'platform', 'company_tax_id', 'doc_date', 'pdf_file', 'store_name'])
        }

#%% sidebar
st.set_page_config(page_icon = Image.open("icon.ico"))
with st.sidebar:
    st.header('✅ VAT Cal', divider = 'orange')
    st.write('#')

    st.subheader('🛒 เลือกจำนวนร้านค้าที่มี')
    store_number = st.selectbox(
        label = 'เลือกจำนวนร้านค้าที่มี', 
        options = [i for i in range(1, 4)],
        label_visibility = 'collapsed'
    )

    st.markdown('<hr style="margin-top: 0px; margin-bottom: 0px;">', unsafe_allow_html=True)

    st.subheader('🛍️ ใส่ชื่อร้านค้า')

    store_name_ls = []
    for i in range(store_number):
        store_name = st.text_input(
            label = f'&nbsp;&nbsp;ร้านค้า #{i + 1}', 
            label_visibility = 'visible'
            )
        if store_name in store_name_ls and store_name != '':
            st.error('ชื่อร้านซ้ำ')
            break

        if '_' in store_name:
            st.error('โปรแกรมไม่รองรับ "_" ในช่องชื่อร้าน')
        store_name_ls.append(store_name)

    st.markdown('<hr style="margin-top: 0px; margin-bottom: 0px;">', unsafe_allow_html=True)
    st.subheader('⚙️ เลือกเมนูคำนวณ')
    sidebar_radio = st.radio(
        label = 'เลือกเมนูคำนวณ',
        options = ['เช็คว่าต้องจด VAT หรือยัง', 'คำนวณ VAT', 'Q&A'], 
        index = 1, 
        label_visibility = 'collapsed'
    )

    # with st.form('📋 วิธีใช้'):
    #     st.write("""วิธีการใช้คร่าว ๆ คือ\n
    #                 1. กดใส่ข้อมูลร้าน\n
    #                 2. อัพโหลดไฟล์\n
    #                 3. กดคำนวณ\n
    #                 4. ส่งไฟล์ผลลัพธ์ไปทาง email\n
    #                 หากมีข้อส่งสัยสามารถสอบถามได้ทาง Page VAT Cal นะครับ""")
#%%
if sidebar_radio == 'เช็คว่าต้องจด VAT หรือยัง':
    before_session_key = st.session_state.keys()

    st.header(f'🔎 {sidebar_radio}', divider='grey')
    
    st.write('')
    st.subheader('1. เลือกปีที่ต้องการตรวจสอบ')
    # st.markdown('<hr style="margin-top: 0px; margin-bottom: 0px;">', unsafe_allow_html=True)
    selected_year = st.selectbox(
        label = "เลือกปีที่ต้องการคำนวณ",
        options = (str(pd.Timestamp.today().year), (str(pd.Timestamp.today().year - 1) + ' (ตรวจสอบว่ายอดถึงเกณฑ์จด VAT ตั้งแต่ปีก่อนหน้าหรือไม่)')), 
        index = None, 
        placeholder = 'เลือกปี',
        label_visibility = 'collapsed'
    )
    st.markdown('<hr style="margin-top: 0px; margin-bottom: 0px;">', unsafe_allow_html=True)
    if selected_year != None:
        selected_year = selected_year.split(' ')[0]
        current_time = pd.to_datetime('today') #+ pd.Timedelta(hours = 7)
        current_day = pd.to_datetime('today').day
        current_year = pd.to_datetime('today').year
        current_month = pd.to_datetime('today').month
        is_full_year = True if current_year - 1 == int(selected_year) else True if current_month == 12 and current_day == 31 else False

    
    ############################################################
        if len([store_name for store_name in store_name_ls if store_name != '']) == store_number:
            st.write('')
            
            for i, store_name in enumerate(store_name_ls):

                st.subheader(f'2.{i + 1} {store_name}')
                st.write('')
                st.markdown(f'<h5>&nbsp;&nbsp;🗂️ เลือก platform ทั้งหมดที่ร้านที่ {store_name} ขายอยู่</h5>', unsafe_allow_html=True)
                selected_platfrom = st.multiselect(
                        label = f'เลือก platform ทั้งหมดที่ร้านที่ **{store_name}** ขายอยู่', 
                        options = ['Shopee', 'Lazada', 'TikTok'], 
                        default = ['Shopee', 'Lazada', 'TikTok'], 
                        placeholder = f'เลือก e-commerce platform อย่างน้อย 1 รายการที่ร้าน {store_name} ขายอยู่', 
                        key = f'selected_platform_{store_name}', 
                        label_visibility = 'collapsed'
                    )
                
                selected_platform = [p for p in ['Shopee', 'Lazada', 'TikTok'] if p in st.session_state[f'selected_platform_{store_name}']]

                st.write('')
                st.markdown(f'<h5>&nbsp;&nbsp;🗂️ Upload ไฟล์ยอดขาย</h5>', unsafe_allow_html=True)

                if selected_platform != []:
                    # if  f'{store_name}_current_select_tab' not in st.session_state:
                    #     st.session_state[f'{store_name}_current_select_tab'] = selected_platform[0]

                    tabs = st.tabs([f'Upload file: {platform}' for platform in selected_platform])
                    for j, tab in enumerate(tabs):
                        with tab:
                            tab_name = selected_platform[j]
                            # st.write(tab_name)
                            st.session_state[f'{store_name}_current_select_tab'] = tab_name
            
                            ################ upload shopee #################
                            if tab_name == 'Shopee': 
                                with st.popover("📥 ดูวิธี Download ไฟล์ยอดขายจาก Shopee", use_container_width = True):
                                    st.write('''
                                        1. Log in เข้า Shopee Seller Center\n
                                        2. เลือก "คำสั่งซื้อของฉัน"\n
                                        3. เลือก "ทั้งหมด"\n
                                        4. กด "ดาวน์โหลด" (ปุ่มด้านขวาบน)\n 
                                        5. เลือกช่วงเวลา**\n
                                        \n
                                        ** **หมายเหตุ**: ระบบของ Shopee ให้ดาวน์โหลดยอดขายได้สูงสุด 1 เดือนต่อการดาวน์โหลด 1 ครั้ง
                                        **แนะนำให้เลือกตั้งแต่วันที่ 1 จนถึงวันสุดท้ายของแต่ละเดือน** และ **ทำการดาวน์โหลดข้อมูลของทุก
                                        เดือน** ในปีที่ต้องการคำนวณ
                                    ''')
                                shopee_files = st.file_uploader(
                                    label = f'** รองรับการอัพโหลดหลายไฟล์พร้อมกัน (.xlsx)', 
                                    accept_multiple_files = True,
                                    type = 'xlsx', 
                                    key = f"sale_file_{store_name}_{tab_name}"
                                )

                                if shopee_files != None and shopee_files != []:
                                    st.success(f'อัพโหลด {len(shopee_files)} ไฟล์ สำเร็จ', icon="✅")
                                else:
                                    st.warning(f'หลังจาก upload ไฟล์สำเร็จ tab นี้จะเปลี่ยนเป็นสีเขียว', icon="ℹ️")
                                
                            ################# upload lazada #################
                            elif tab_name == 'Lazada':
                                with st.popover("📥 กดดูวิธี Download ไฟล์ยอดขายจาก Lazada", use_container_width = True):
                                    st.write('''
                                        1. Log in เข้า Lazada Seller Center
                                        2. เลือก "คำสั่งซื้อ"\n
                                        3. เลือก "ทั้งหมด"\n
                                        4. ในช่อง "วันที่สั่งซื้อ" --> เลือก "กำหนดเอง" และเลือกช่วยเวลา (สามาถเลือกได้ทั้งปี)\n 
                                        5. เลือก "Export" และเลือก "Export All"\n
                                    ''')
                                lazada_file = st.file_uploader(
                                    label = f'** รองรับการอัพโหลด 1 ไฟล์ (.xlsx)', 
                                    accept_multiple_files = False, 
                                    type = 'xlsx',
                                    key = f'sale_file_{store_name}_{tab_name}'
                                )
                                if lazada_file != None:
                                    st.success(f'สำเร็จ', icon="✅")
                                else:
                                    st.warning(f'หลังจาก upload ไฟล์สำเร็จ tab นี้จะเปลี่ยนเป็นสีเขียว', icon="ℹ️")

                            ################# upload TikTok #################
                            elif tab_name == 'TikTok':    
                                with st.popover("📥 ดูวิธี Download ไฟล์ยอดขายจาก TikTok", use_container_width = True):
                                    st.write('''
                                        1. Log in เข้า TikTok Seller Center
                                        2. เลือก "คำสั่งซื้อ" -> "จัดการคำสั่งซื้อ"\n
                                        3. เลือก "ทั้งหมด"\n
                                        4. เลือก "ตัวกรอง"\n 
                                        5. ในช่อง "เวลาที่สร้าง" ให้ทำการเลือกช่วยเวลาที่ต้องการ (สามาถเลือกได้ทั้งปี)\n
                                        6. เลือก "นำไปใช้"\n
                                        7. เลือก "ดาวน์โหลด"\n
                                        8. เลือก "CSV" และกด "ส่งออก"\n
                                        9. กด "ดาวน์โหลด"\n     
                                    ''')
                                tiktok_file = st.file_uploader(
                                    label = f'** รองรับการอัพโหลด 1 ไฟล์ (.csv)', 
                                    accept_multiple_files = False, 
                                    type = 'csv',
                                    key = f'sale_file_{store_name}_{tab_name}'
                                )   
                                if tiktok_file != None:
                                    st.success(f'สำเร็จ', icon="✅")
                                else:
                                    st.warning(f'หลังจาก upload ไฟล์สำเร็จ tab นี้จะเปลี่ยนเป็นสีเขียว', icon="ℹ️")
            
                for platform in ['Shopee', 'Lazada', 'TikTok']:
                    if platform not in selected_platform:
                        if f'sale_file_{store_name}_{platform}' in st.session_state.keys():
                            del st.session_state[f'sale_file_{store_name}_{platform}']
                
                st.markdown('<hr style="margin-top: 0px; margin-bottom: 0px;">', unsafe_allow_html=True)
            
            del_ls = []
            for key in st.session_state:
                if 'selected_platform' in key:
                    store_name = key.replace('selected_platform_', '')
                    if store_name not in store_name_ls:
                        if key in st.session_state.keys():
                            del st.session_state[key]
                        # if f'{store_name}_current_select_tab' in st.session_state.keys():
                        #     del st.session_state[f'{store_name}_current_select_tab']
                        if f'sale_file_{store_name}_Shopee' in st.session_state.keys():
                            del st.session_state[f'sale_file_{store_name}_Shopee']
                        if f'sale_file_{store_name}_Lazada' in st.session_state.keys():
                            del st.session_state[f'sale_file_{store_name}_Lazada']
                        if f'sale_file_{store_name}_TikTok' in st.session_state.keys():
                            del st.session_state[f'sale_file_{store_name}_TikTok']

            selected_platform_d = {key: value for key, value in st.session_state.items() if 'selected_platform' in key if value != []}
            check_ls = []
            if selected_platform_d != {}:
                for store, platform_ls in selected_platform_d.items():
                    store_name = store.replace('selected_platform_', '')
                    for platform in platform_ls:
                        if f'sale_file_{store_name}_{platform}' not in st.session_state.keys():
                            check_ls.append(f'ร้าน {store_name} {platform}')
                        else:
                            if st.session_state[f'sale_file_{store_name}_{platform}'] == None or st.session_state[f'sale_file_{store_name}_{platform}'] == []:
                                check_ls.append(f'ร้าน {store_name} ({platform})')
            else:
                check_ls.append('')

            if check_ls == []: #อัพโหลดข้อมูลครบแล้ว
                if 'calculate_clicked' not in st.session_state or before_session_key != st.session_state.keys():
                    st.session_state['calculate_clicked'] = False

                cont = False
                col1, col2, col3 = st.columns(3)
                
                with col2:
                    st.write('')
                    if st.button('📬 คำนวณ', use_container_width = True):
                        st.session_state['calculate_clicked'] = True
                        # cont = True

                if st.session_state['calculate_clicked']:
                    st.write('')
                    st.subheader('3. รายงานผลการคำนวณ')
                    
                    st.session_state['total_sale'] = 0

                    st.session_state['df_dict'] = {}
    
                    cont=True
                    for key, value in st.session_state.items():
                        if 'sale_file' in key and 'Shopee' in key:
                            store = key.split('_')[-2]
                            if store not in st.session_state['df_dict'].keys():
                                st.session_state['df_dict'][store] = {}

                            shopee_result_df = total_sale_shopee(shopee_file_ls = value, selected_year = selected_year, store = store, is_full_year=is_full_year, current_month = current_month)
                            if shopee_result_df is not None and not shopee_result_df.empty:
                                st.session_state['total_sale'] += shopee_result_df[store+'_shopee']['order_value'].sum() + shopee_result_df[store+'_shopee']['shipping_value'].sum()
                                st.session_state['df_dict'][store]['Shopee'] = shopee_result_df
                            else:
                                cont = False

                        elif 'sale_file' in key and 'Lazada' in key:
                            store = key.split('_')[-2]
                            if store not in st.session_state['df_dict'].keys():
                                st.session_state['df_dict'][store] = {}

                            lazada_result_df = total_sale_lazada(lazada_file = value, selected_year = selected_year, store = store, is_full_year = is_full_year, current_month = current_month)
                            if lazada_result_df is not None and not lazada_result_df.empty:
                                st.session_state['total_sale'] += lazada_result_df[store+'_lazada']['order_value'].sum() + lazada_result_df[store+'_lazada']['shipping_value'].sum()
                                st.session_state['df_dict'][store]['Lazada'] = lazada_result_df
                            else: 
                                cont = False
                        
                        elif 'sale_file' in key and 'TikTok' in key:
                            store = key.split('_')[-2]
                            if store not in st.session_state['df_dict'].keys():
                                st.session_state['df_dict'][store] = {}

                            tiktok_result_df = total_sale_tiktok(tiktok_file = value, selected_year = selected_year, store = store, is_full_year = is_full_year, current_month = current_month)
                                
                            # st.write(tiktok_result_df.empty)
                            if tiktok_result_df is not None and not tiktok_result_df.empty:
                                st.session_state['total_sale'] += tiktok_result_df[store+'_tiktok']['order_value'].sum() + tiktok_result_df[store+'_tiktok']['shipping_value'].sum()
                                st.session_state['df_dict'][store]['TikTok'] = tiktok_result_df
                            else:
                                cont = False

                    if cont:
                        
                        if 'result_df' not in st.session_state:
                            st.session_state['result_df'] = pd.DataFrame()
                    
                        result_df = pd.DataFrame()
                        # st.write(st.session_state)
                        for store_name, store_dict in st.session_state['df_dict'].items():
                            for platform in ['Shopee', 'Lazada', 'TikTok']:
                                if platform in store_dict.keys():
                                    df = store_dict[platform]
                                    result_df = pd.concat([result_df, df], axis = 1)
                        
                        result_df['sum'] = result_df.sum(axis = 1)
                        result_df['cumsum'] = result_df['sum'].cumsum()

                        st.session_state['result_df'] = result_df
                        
                        if st.session_state['result_df'][st.session_state['result_df']['cumsum'] >= 1800000].shape[0] > 0:
                            col1, col2, col3 = st.columns(3)
                            col1.metric("ต้องจด VAT แล้วหรือยัง?", 
                                        "🔴 Yes", 
                                        border = True
                                        )
                            col2.metric(f"ยอดขายรวมปี {selected_year}", 
                                        '{:.2f} M'.format(st.session_state['total_sale']/1000000),
                                        border = True
                                        )
                            col3.metric('ยอดถึง 1.8 M ตั้งแต่',
                                        pd.to_datetime(result_df[result_df["cumsum"] >= 1800000].index[0], format = "%Y-%m-%d").strftime("%d %b %Y"), 
                                        border = True
                                        )
                        
                        else:
                            if st.session_state['result_df'][st.session_state['result_df']['cumsum'] >= 1800000].shape[0] > 1500000 and st.session_state['result_df'][st.session_state['result_df']['cumsum'] >= 1800000].shape[0] < 1800000:
                                col1, col2 = st.columns(2)
                                col1.metric("ต้องจด VAT แล้วหรือยัง?", 
                                            "🟡 No", 
                                            border = True
                                            )
                            else:
                                col1, col2 = st.columns(2)
                                col1.metric("ต้องจด VAT แล้วหรือยัง?", 
                                            "🟢 No", 
                                            border = True
                                            )
                                
                            col2.metric("ยอดขายรวม", 
                                        '{:.2f} M'.format(st.session_state['total_sale']/1000000),
                                        border = True
                                        )

                            
                        st.markdown('<hr style="margin-top: 0px; margin-bottom: 0px;">', unsafe_allow_html=True)
                        st.write('')
                        st.write('')
                        # st.subheader('4. ดาวน์โหลดไฟล์')

                        # Initialize session state for buttons
                        if "form_submitted" not in st.session_state:
                            st.session_state.form_submitted = False  # Tracks form submission


                        # **Only show form if calculation is completed**
                        if 'result_df' in st.session_state.keys():
                            with st.form("my_form"):
                                st.markdown(f'<h5 style="text-align: center">&nbsp;&nbsp;📋 กรอกข้อมูลเพื่อรับไฟล์ผลคำนวณทาง Email 📋</h5>', unsafe_allow_html=True)

                                email_input = st.text_input("📧 Email", placeholder="your-email@email.com")
                                email_valid = True
                                if email_input:
                                    if '@' not in email_input:
                                        st.error('🚨 Email ผิด format (ต้องมี @)')
                                        email_valid = False
                                    elif email_input.split('@')[-1] not in ['gmail.com', 'yahoo.com', 'yahoo.co.th', 'outlook.com', 'hotmail.com', 'live.com']:
                                        st.error('🚨 รองรับแค่ gmail, yahoo, outlook, hotmail, live')
                                        email_valid = False
                                else:
                                    email_valid = False  # Email is required

                                user_name = st.text_input("👤 ชื่อ")
                                user_surname = st.text_input("👤 นามสกุล")
                                
                                user_type = st.radio("📌 ประเภทผู้ใช้", ["บุคคลธรรมดา", "นิติบุคคล"], index=0, horizontal=True)
                                agree = st.checkbox("✅ ฉันยินยอมให้ใช้ข้อมูลเพื่อพัฒนาเครื่องมือคำนวณ VAT")

                                col1, col2, col3 = st.columns(3)
                                with col2:
                                    submit_button = st.form_submit_button("📩 ส่งไฟล์ผลการคำนวณ", use_container_width=True)

                            # **Handle Form Submission**
                            if submit_button:
                                if email_input.strip() and user_name.strip() and user_surname.strip() and agree:
                                    st.session_state.form_submitted = True  # Mark form as submitted
                                    st.success("✅ ข้อมูลถูกต้อง! ส่งอีเมล...")
                                else:
                                    st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนก่อนกด Submit!")

                        # # Gmail credentials
                        EMAIL_SENDER = st.secrets["email"]["EMAIL_SENDER"]
                        EMAIL_PASSWORD = st.secrets["email"]["EMAIL_PASSWORD"]  # Use App Password if 2FA is enabled

                        def send_email_with_attachment(receiver_email, df):
                            """Send an email with an in-memory Excel file containing the calculated DataFrame."""
                            try:
                                # Convert DataFrame to an in-memory Excel file
                                excel_buffer = io.BytesIO()
                                with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
                                    df.to_excel(writer, sheet_name="Total Sale Report")
                                excel_buffer.seek(0)  # Move to the beginning of the buffer

                                # Create email message
                                msg = EmailMessage()
                                msg["From"] = EMAIL_SENDER
                                msg["To"] = receiver_email,
                                msg["Subject"] = f"รายงานการคำนวณยอดขายรวม ปี {selected_year}"
                                msg.set_content("Attached is your total sale calculation report.")

                                # Attach in-memory Excel file
                                msg.add_attachment(
                                    excel_buffer.read(),
                                    maintype="application",
                                    subtype="vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    filename=f"รายงานยอดขายปี {selected_year}.xlsx"
                                )

                                # Send email via Gmail SMTP server
                                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                                    server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                                    server.send_message(msg)

                                # st.success(f"✅ Email sent to {receiver_email}")
                                return True

                            except Exception as e:
                                st.error(f"❌ Error: {e}")
                                return False

                        # **Show Confirmation Message After Form Submission**
                        if st.session_state.form_submitted:
                            gdrive_credentials = json.loads(st.secrets["gdrive"]["GOOGLE_SHEETS_CREDENTIALS"])
                            scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
                            cerds = ServiceAccountCredentials.from_json_keyfile_dict(gdrive_credentials, scope)
                            client = gspread.authorize(cerds)
                            sheet = client.open("user_data").worksheet('check1.8') # เป็นการเปิดไปยังหน้าชีตนั้นๆ

                            sheet.append_row([
                                'check1.8', 
                                selected_year,
                                current_time.strftime('%Y-%m-%d %H:%M:%S'),
                                user_type,
                                user_name, 
                                user_surname, 
                                ', '.join(store_name_ls),
                                email_input,
                                st.session_state['total_sale']
                            ])
                        
                            send_email_with_attachment(receiver_email = email_input, df = result_df)
                            st.success(f"📩 อีเมลของคุณถูกส่งไปยัง {email_input} เรียบร้อยแล้ว!")


                        

            else:
                st.warning('ปุ่มคำนวณจะแสดงหลังจากอัพโหลดไฟล์ยอดขายครบทุกไฟล์', icon = 'ℹ️')
        else:
            st.error('ใส่ชื่อร้านค้าที่ tab ด้านข้างให้ครบ', icon="🚨")
    else:
        pass
######################        
elif sidebar_radio == 'คำนวณ VAT':
    before_session_key = st.session_state.keys()
    
    st.header(f'🧾 {sidebar_radio}', divider = 'grey')
    st.write('')

    st.subheader('1. เลือกเดือนที่ต้องการคำนวณ VAT')
    selected_month = st.selectbox(
        label = 'select_month', 
        options = ([(pd.to_datetime('today').replace(day = 1) - pd.DateOffset(months = i)).strftime('%Y-%m') for i in range(1, 7)]), 
        index = 0, 
        placeholder = 'เลือกเดือน',
        label_visibility = 'collapsed'
    )
    month = pd.to_datetime(selected_month.split('-')[-1], format = '%m').month
    year = pd.to_datetime(selected_month.split('-')[0], format = '%Y').year

    st.markdown('<hr style="margin-top: 0px; margin-bottom: 0px;">', unsafe_allow_html=True)


    if len([store_name for store_name in store_name_ls if store_name != '']) == store_number:
        st.write('')
            
        for i, store_name in enumerate(store_name_ls):
            st.subheader(f'2.{i + 1} {store_name}')
            st.write('')
            st.markdown(f'<h5>&nbsp;&nbsp;🗂️ เลือก platform ทั้งหมดที่ร้านที่ {store_name} ขายอยู่</h5>', unsafe_allow_html=True)
            selected_platfrom = st.multiselect(
                    label = f'เลือก platform ทั้งหมดที่ร้านที่ **{store_name}** ขายอยู่', 
                    options = ['Shopee', 'Lazada', 'TikTok'], 
                    default = ['Shopee', 'Lazada', 'TikTok'], 
                    placeholder = f'เลือก e-commerce platform อย่างน้อย 1 รายการที่ร้าน {store_name} ขายอยู่', 
                    key = f'selected_platform_{store_name}', 
                    label_visibility = 'collapsed'
                )
            
            selected_platform = [p for p in ['Shopee', 'Lazada', 'TikTok'] if p in st.session_state[f'selected_platform_{store_name}']]

            st.write('')
            st.markdown(f'<h5>&nbsp;&nbsp;🗂️ Upload ไฟล์ยอดขาย</h5>', unsafe_allow_html=True)

            if selected_platform != []:
                # if  f'{store_name}_current_select_tab' not in st.session_state:
                #     st.session_state[f'{store_name}_current_select_sale_tab'] = selected_platform[0]

                sale_tabs = st.tabs([f'Upload file ยอดขาย: {platform}' for platform in selected_platform])
                for j, sale_tab in enumerate(sale_tabs):
                    with sale_tab:
                        sale_tab_name = selected_platform[j]
                        # st.write(tab_name)
                        # st.session_state[f'{store_name}_current_select_sale_tab'] = sale_tab_name
        
                        ################ upload shopee #################
                        if sale_tab_name == 'Shopee': 
                            with st.popover("📥 กดดูวิธี Download ไฟล์ยอดขายจาก Shopee", use_container_width = True):
                                st.write('''
                                    1. Log in เข้า Shopee Seller Center\n
                                    2. เลือก "คำสั่งซื้อของฉัน"\n
                                    3. เลือก "ทั้งหมด"\n
                                    4. เลือก "ดาวน์โหลด"\n 
                                    5. เลือกช่วงเวลา\n
                                    \n
                                    ** **หมายเหตุ**: ให้กดเลือกตั้งแต่วันแรกถึงวันสุดท้ายของเดือนที่ต้องการคำนวณ VAT
                                ''')
                            shopee_monthly_sale_file = st.file_uploader(
                                label = f'** รองรับการอัพโหลด 1 ไฟล์ (.xlsx)', 
                                accept_multiple_files = False,
                                type = 'xlsx', 
                                key = f"monthly_sale_file_{store_name}_{sale_tab_name}"
                            )

                            if shopee_monthly_sale_file != None and shopee_monthly_sale_file != []:
                                st.success(f'อัพโหลดไฟล์ สำเร็จ', icon="✅")
                            else:
                                st.warning(f'หลังจากอัพโหลดไฟล์ยอดขายจาก Shopee สำเร็จแล้ว tab จะเปลี่ยนเป็นสีเขียว', icon="ℹ️")
                            
                        ################# upload lazada #################
                        elif sale_tab_name == 'Lazada':
                            with st.popover("📥 กดดูวิธี Download ไฟล์ยอดขายจาก Lazada", use_container_width = True):
                                st.write('''
                                    1. Log in เข้า Lazada Seller Center
                                    2. เลือก "คำสั่งซื้อ"\n
                                    3. เลือก "ทั้งหมด"\n
                                    4. ในช่อง "วันที่สั่งซื้อ" -> "กำหนดเอง" และเลือกช่วยเวลา\n 
                                    5. เลือก "Export" และเลือก "Export All"\n
                                ''')
                            lazada_monthly_sale_file = st.file_uploader(
                                label = f'** รองรับการอัพโหลด 1 ไฟล์ (.xlsx)', 
                                accept_multiple_files = False, 
                                type = 'xlsx',
                                key = f'monthly_sale_file_{store_name}_{sale_tab_name}'
                            )
                            if lazada_monthly_sale_file != None:
                                st.success(f'สำเร็จ', icon="✅")
                            else:
                                st.warning(f'หลังจากอัพโหลดไฟล์ยอดขายจาก Lazada สำเร็จแล้ว tab จะเปลี่ยนเป็นสีเขียว', icon="ℹ️")

                        ################# upload TikTok #################
                        elif sale_tab_name == 'TikTok':    
                            with st.popover("📥 กดดูวิธี Download ไฟล์ยอดขายจาก TikTok", use_container_width = True):
                                st.write('''
                                    1. Log in เข้า TikTok Seller Center
                                    2. เลือก "คำสั่งซื้อ" -> "จัดการคำสั่งซื้อ"\n
                                    3. เลือก "ทั้งหมด"\n
                                    4. เลือก "ตัวกรอง"\n 
                                    5. ในช่อง "เวลาที่สร้าง" ให้ทำการเลือกช่วยเวลาที่ต้องการ\n
                                    6. เลือก "นำไปใช้"\n
                                    7. เลือก "ดาวน์โหลด"\n
                                    8. เลือก "CSV" และกด "ส่งออก"\n
                                    9. กด "ดาวน์โหลด"\n     
                                ''')
                            tiktok_monthly_sale_file = st.file_uploader(
                                label = f'** รองรับการอัพโหลด 1 ไฟล์ (.xlsx)', 
                                accept_multiple_files = False, 
                                type = 'csv',
                                key = f'monthly_sale_file_{store_name}_{sale_tab_name}'
                            )   
                            if tiktok_monthly_sale_file != None:
                                st.success(f'สำเร็จ', icon="✅")
                            else:
                                st.warning(f'หลังจากอัพโหลดไฟล์ยอดขายจาก TikTok สำเร็จแล้ว tab จะเปลี่ยนเป็นสีเขียว', icon="ℹ️")

                st.write('')
                st.markdown(f'<h5>&nbsp;&nbsp;🗂️ Upload ไฟล์ใบเสร็จค่าธรรมเนียม</h5>', unsafe_allow_html=True)

                commission_tabs = st.tabs([f'Upload file ค่าธรรมเนียม: {platform}' for platform in selected_platform])
                for k, commission_tab in enumerate(commission_tabs):
                    with commission_tab:
                        commission_tab_name = selected_platform[k]
                        # st.write(tab_name)
                        # st.session_state[f'{store_name}_current_select_commission_tab'] = commission_tab_name

                        if commission_tab_name == 'Shopee': 
                            with st.popover("📥 กดดูวิธี Download ไฟล์ค่าธรรมเนียม Shopee", use_container_width = True):
                                st.write('''
                                    1. Log in เข้า Shopee Seller Center
                                    2. ที่ tab ด้านซ้าย เลือก "รายรับของฉัน"\n
                                    3. ที่ tab ด้านขวา เลือก "My Tax Invoices"\n
                                    4. ในหน้า "ระบบออกใบกำกับภาษี เลือก "ดาวน์โหลดใบเสร็จรับเงินและใบกำกับภาษีอิเล็กทรอนิกส์เต็มรูป"\n 
                                    5. เลือกช่วงเวลาตั้งแต่วันแรก จนถึงวันสุดท้ายของเดือนที่ต้องการคำนวณ VAT\n
                                    6. กด "ดาวน์โหลดทั้งหมด"\n
                                ''')
                            shopee_commission_file = st.file_uploader(
                                label = f'** รองรับการอัพโหลด 1 ไฟล์ (.zip)', 
                                accept_multiple_files = False,
                                type = 'zip', 
                                key = f"commission_file_{store_name}_{commission_tab_name}"
                            )

                            if shopee_commission_file != None:
                                st.success(f'อัพโหลดไฟล์ สำเร็จ', icon="✅")
                            else:
                                st.warning(f'หลังจากอัพโหลดไฟล์ค่าธรรมเนียม Shopee สำเร็จแล้ว tab จะเปลี่ยนเป็นสีเขียว', icon="ℹ️")

                        elif commission_tab_name == 'Lazada':
                            with st.popover("📥 กดดูวิธี Download ไฟล์ยอดขายจาก Lazada", use_container_width = True):
                                st.write('''
                                    1. Log in เข้า Lazada Seller Center
                                    2. ที่ tab "การเงิน" เลือก "รายรับของฉัน"\n
                                    3. เลือก "ใบแจ้งหนี้และใบลดหนี้"\n
                                    4. ที่ tab "ผู้บริการให้ใบแจ้งหนี้" เลือก "LAZADA"\n 
                                    5. เลือกใบเสร็จค่าธรรมเนียมที่มี "รอบบิล" ตรงกับเดือนที่ต้องการคำนวณ VAT\n
                                ''')
                                st.warning('LAZADA ออกใบเสร็จรายสัปดาห์ ในกรณีที่เป็นสัปดาห์คร่อมเดือนในช่วงต้นเดือน เลือก "ใบแจ้งหนี้" และในกรณีที่เป็นสัปดาห์คร่อมปลายเดือน ให้เลือก "ใบแจ้งหนี (สิ้นเดือน)"', icon="ℹ️")
                            lazada_commission_files = st.file_uploader(
                                label = f'** รองรับการอัพโหลดหลายไฟล์พร้อมกัน (.pdf)', 
                                accept_multiple_files = True, 
                                type = 'pdf',
                                key = f'commission_file_{store_name}_{commission_tab_name}'
                            )
                            if lazada_commission_files != None and lazada_commission_files != []:
                                st.success(f'อัพโหลดไฟล์ {len(lazada_commission_files)} ไฟล์สำเร็จ', icon="✅")
                            else:
                                st.warning(f'หลังจากอัพโหลดไฟล์ค่าธรรมเนียม Shopee สำเร็จแล้ว tab จะเปลี่ยนเป็นสีเขียว', icon="ℹ️")

                        elif commission_tab_name == 'TikTok':
                            with st.popover("📥 กดดูวิธี Download ไฟล์ค่าธรรมเนียม TikTok", use_container_width = True):
                                st.write('''
                                    1. Log in เข้า TikTok Seller Center
                                    2. ที่ tab "การเงิน" เลือก "ใบแจ้งหนี้"\n
                                    3. กด "ดาวน์โหลดเป็นชุด"\n
                                    4. เลือก "ค่าบริการแพลตฟอร์ม"\n 
                                    5. กดเลือกเดือนที่ต้องการคำนวณ VAT\n
                                    6. เลือก "สามเดือนที่แล้ว"
                                ''')
                                st.warning('TikTok ออกใบเสร็จรายสัปดาห์ ใบเสร็จที่คร่อมเดือนในช่วงสัปดาห์แรกของเดือนมักจะอยู่ในไฟล์ของเดือนก่อนหน้า ฉนั้น เวลาดาวโหลดไฟล์จึงควรเลือก "สามเดือนที่แล้ว"', icon="ℹ️")
                            tiktok_commission_file = st.file_uploader(
                                label = f'** รองรับการอัพโหลด 1 ไฟล์ (.zip)', 
                                accept_multiple_files = False,
                                type = 'zip', 
                                key = f"commission_file_{store_name}_{commission_tab_name}"
                            )

                            if tiktok_commission_file != None:
                                st.success(f'อัพโหลดไฟล์ สำเร็จ', icon="✅")
                            else:
                                st.warning(f'หลังจากอัพโหลดไฟล์ค่าธรรมเนียม Shopee สำเร็จแล้ว tab จะเปลี่ยนเป็นสีเขียว', icon="ℹ️")
                # st.write('')
                st.markdown('<hr style="margin-top: 0px; margin-bottom: 0px;">', unsafe_allow_html=True)

            # คนใช้ ลบข้อมูล tab platform ที่ขายออกไป
            
            for platform in ['Shopee', 'Lazada', 'TikTok']:
                if platform not in selected_platform:
                    if f'monthly_sale_file_{store_name}_{platform}' in st.session_state.keys():
                        del st.session_state[f'monthly_sale_file_{store_name}_{platform}']
                    if f"commission_file_{store_name}_{platform}" in st.session_state.keys():
                        del st.session_state[f"commission_file_{store_name}_{platform}"]
            
            st.write('')
            # st.markdown('<hr style="margin-top: 0px; margin-bottom: 0px;">', unsafe_allow_html=True)

        #คนใช้ ลบลข้อมูลร้านค้าไป
        del_ls = []
        for key in st.session_state:
            if 'selected_platform' in key:
                store_name = key.replace('selected_platform_', '')
                if store_name not in store_name_ls:
                    if key in st.session_state.keys():
                        del st.session_state[key]
                    # if f'{store_name}_current_select_sale_tab' in st.session_state.keys():
                    #     del st.session_state[f'{store_name}_current_select_sale_tab']
                    # if f'{store_name}_current_select_commission_tab' in st.session_state.keys():
                    #     del st.session_state[f'{store_name}_current_select_commission_tab']
                    if f'monthly_sale_file_{store_name}_Shopee' in st.session_state.keys():
                        del st.session_state[f'monthly_sale_file_{store_name}_Shopee']
                    if f'monthly_sale_file_{store_name}_Lazada' in st.session_state.keys():
                        del st.session_state[f'monthly_sale_file_{store_name}_Lazada']
                    if f'monthly_sale_file_{store_name}_TikTok' in st.session_state.keys():
                        del st.session_state[f'monthly_sale_file_{store_name}_TikTok']
                    if f'commission_file_{store_name}_Shopee' in st.session_state.keys():
                        del st.session_state[f'commission_file_{store_name}_Shopee']
                    if f'commission_file_{store_name}_Lazada' in st.session_state.keys():
                        del st.session_state[f'commission_file_{store_name}_Lazada']
                    if f'commission_file_{store_name}_TikTok' in st.session_state.keys():
                        del st.session_state[f'commission_file_{store_name}_TikTok']
        # st.write(st.session_state)


        selected_platform_d = {key: value for key, value in st.session_state.items() if 'selected_platform' in key if value != []}
        # st.write(selected_platform_d)
        check_ls = []
        if selected_platform_d != {}:
            for store, platform_ls in selected_platform_d.items():
                store_name = store.replace('selected_platform_', '')
                for platform in platform_ls:
                    if f'monthly_sale_file_{store_name}_{platform}' not in st.session_state.keys():
                        check_ls.append(f'ไฟล์ยอดขาย ร้าน {store_name} {platform}')
                    else:
                        if st.session_state[f'monthly_sale_file_{store_name}_{platform}'] == None or st.session_state[f'monthly_sale_file_{store_name}_{platform}'] == []:
                            check_ls.append(f'ไฟล์ยอดขาย ร้าน {store_name} ({platform})')

                    if f'commission_file_{store_name}_{platform}' not in st.session_state.keys():
                        check_ls.append(f'ไฟล์ค่าธรรมเนียม ร้าน {store_name} {platform}')
                    else:
                        if st.session_state[f'commission_file_{store_name}_{platform}'] == None or st.session_state[f'commission_file_{store_name}_{platform}'] == []:
                            check_ls.append(f'ไฟล์ค่าธรรมเนียม ร้าน {store_name} ({platform})')

        else:
            check_ls.append('')


        if check_ls == []: #อัพโหลดข้อมูลครบแล้ว
            if 'vat_calculate_clicked' not in st.session_state or before_session_key != st.session_state.keys():
                st.session_state['vat_calculate_clicked'] = False

            if "selected_tax_id" not in st.session_state:
                st.session_state.selected_tax_id = set()
            
            if 'sale_d' not in st.session_state:
                st.session_state['sale_d'] = {}
            
            if 'commission_d' not in st.session_state:
                st.session_state['commission_d'] = {}
            

            cal_col1, cal_col2, cal_col3 = st.columns([2, 1, 2])
            with cal_col2:
                if st.button('📬 คำนวณ', use_container_width = True):
                    st.session_state['vat_calculate_clicked'] = True
                    st.session_state.selected_tax_id = set()

            if st.session_state.vat_calculate_clicked:
                #ทุกครั้งที่กดปุ่มคำนวณ ให้ reset แล้วเป็น {} ใหม่ เพราะกลัวไปผิดกับอันเดิม
                st.session_state['sale_d'] = {}
                st.session_state['commission_d'] = {}

                cont=True
                for key, value in st.session_state.items(): #value = uploaded file
                    # if value != None:
                    ############## sale ##############
                    if 'monthly_sale_file_' in key and 'Shopee' in key:
                        store = key.split('_')[-2]
                        if store not in st.session_state['sale_d'].keys():
                            st.session_state['sale_d'][store] = {}

                        st.session_state['sale_d'][store]['Shopee'] = vat_cal_sale_shopee(shopee_sale_file = value, year = year, store = store, month = month)

                    elif 'monthly_sale_file_' in key and 'Lazada' in key:
                        store = key.split('_')[-2]
                        if store not in st.session_state['sale_d'].keys():
                            st.session_state['sale_d'][store] = {}

                        st.session_state['sale_d'][store]['Lazada'] = vat_cal_sale_lazada(lazada_sale_file = value, year = year, store = store, month = month)

                    elif 'monthly_sale_file_' in key and 'TikTok' in key:
                        store = key.split('_')[-2]
                        if store not in st.session_state['sale_d'].keys():
                            st.session_state['sale_d'][store] = {}

                        st.session_state['sale_d'][store]['TikTok'] = vat_cal_sale_tiktok(tiktok_sale_file = value, year = year, store = store, month = month)

                    ############## commission ##############
                    elif 'commission_file_' in key and 'Shopee' in key:
                        store = key.split('_')[-2]
                        if store not in st.session_state['commission_d'].keys():
                            st.session_state['commission_d'][store] = {}

                        st.session_state['commission_d'][store]['Shopee'] = vat_cal_commission_shopee(store_name = store, shopee_zip_file = value, month = month, year = year) 

                    elif 'commission_file_' in key and 'Lazada' in key:
                        store = key.split('_')[-2]
                        if store not in st.session_state['commission_d'].keys():
                            st.session_state['commission_d'][store] = {}

                        st.session_state['commission_d'][store]['Lazada'] = vat_cal_commission_lazada(store_name = store, lazada_file_ls = value, month = month, year = year)

                    elif 'commission_file_' in key and 'TikTok' in key:
                        store = key.split('_')[-2]

                        if store not in st.session_state['commission_d'].keys():
                            st.session_state['commission_d'][store] = {}

                        st.session_state['commission_d'][store]['TikTok'] = vat_cal_commission_tiktok(store_name = store, tiktok_zip_file = value, month = month, year =year) 
            
                    
                    # else:
                        #ไม่มีไฟล์ของร้านนี้
                        # pass

                # st.write(st.session_state)
                ############# merge data ##############  
                sale_df = pd.DataFrame()
                commission_df = pd.DataFrame()
                pdf_df = pd.DataFrame()
                for store in store_name_ls:
                    for platform in ['Shopee', 'Lazada', 'TikTok']:
                        if store in st.session_state['sale_d'].keys():
                            if platform in st.session_state['sale_d'][store].keys() and platform in st.session_state[f'selected_platform_{store}']:
                                sale_df = pd.concat([sale_df, st.session_state['sale_d'][store][platform]])

                        if store in st.session_state['commission_d'].keys():
                            if platform in st.session_state['commission_d'][store].keys() and platform in st.session_state[f'selected_platform_{store}']:
                                commission_df = pd.concat([commission_df, st.session_state['commission_d'][store][platform]['commission_df']], axis = 0).reset_index(drop = True)
                                pdf_df = pd.concat([pdf_df, st.session_state['commission_d'][store][platform]['pdf_df']], axis = 0).reset_index(drop = True)


                # มีชื่อในใบเสร็จค่าคอมมิชชั้นมากกว่า 1 ชื่อ --> split df
                if len(commission_df['company_tax_id'].str.lower().str.replace(' ', '').unique()) > 1:
                    st.subheader('5. check')
                    st.warning('เจอชื่อ บ ในใบเสร็จ มากกว่า 1 ชื่อ --> กรุณาเลือกชื่อผู้จ่าย VAT ที่ถูกต้อง', icon="⚠️")

                    unique_company_tax_id = commission_df['company_tax_id'].str.replace(' ', '').unique().tolist()

                    for tax_id in unique_company_tax_id:
                        # Create a section for each unique name
                        name = commission_df[commission_df['company_tax_id'] == tax_id]['company_name'].tolist()[0]
                        is_checked = st.checkbox(name, key = f"checkbox_{tax_id}")

                        # Update the set of selected names based on the checkbox state
                        if is_checked:
                            st.session_state.selected_tax_id.add(tax_id)
                        else:
                            st.session_state.selected_tax_id.discard(tax_id)

                        # Show filtered dataframe for the name
                        filtered_commission_df = commission_df[commission_df["company_tax_id"] == tax_id]
                        # filtered_pdf_df = pdf_df[pdf_df['company_tax_id']== tax_id]
                        # st.dataframe(filtered_pdf_df)
                        st.dataframe(filtered_commission_df)

                    finish_tick_col1, finish_tick_col2, finish_tick_col3 = st.columns([2, 1, 2])
                    with finish_tick_col2:
                        if st.button('เลือกเสร็จแล้วให้คลิกที่นี่', use_container_width=True):
                            commission_df1 = commission_df[commission_df["company_tax_id"].isin(st.session_state['selected_tax_id'])].sort_values(by = ['store_name', 'platform', 'doc_date', 'doc_num'], ascending = [True, True, True, True]).reset_index(drop = True)

                            pdf_df1 = pdf_df[pdf_df["company_tax_id"].isin(st.session_state['selected_tax_id'])].sort_values(by = ['store_name', 'platform', 'doc_date', 'doc_num'], ascending = [True, True, True, True]).reset_index(drop = True)
                            
                            ready_to_download = True
                            # st.divider()
                        else:
                            ready_to_download = False
                
                    
                else: 
                    ready_to_download = True
                    commission_df1 = commission_df.sort_values(by = ['store_name', 'platform', 'doc_date', 'doc_num'], ascending = [True, True, True, True]).reset_index(drop = True)
                    pdf_df1 = pdf_df
                    # st.divider()

                if ready_to_download:
                    vat_report_col1, vat_report_col2, vat_report_col3 = st.columns(3)
                    vat_report_col1.metric(
                        label = 'ภาษีขาย (THB)', 
                        value = "{:,.2f}".format(sale_df["vat"].sum()), 
                        border = True
                    )
                    vat_report_col2.metric(
                        label = 'ภาษีซื้อ (THB)', 
                        value = "{:,.2f}".format(commission_df1["vat"].sum()), 
                        border = True
                    )
                    vat_report_col3.metric(
                        label = 'VAT ที่ต้องจ่าย (THB)', 
                        value = "{:,.2f}".format(sale_df["vat"].sum() - commission_df1["vat"].sum()), 
                        border = True
                    )

                merged_pdf_d = {}
                for store in pdf_df1['store_name'].unique():
                    
                    df1 = pdf_df1[pdf_df1['store_name'] == store].reset_index(drop = True)
                    
                    for platform in df1['platform'].unique():
                        df2 = df1[df1['platform'] == platform].reset_index(drop = True)

                        merger = PdfMerger()
                        for pdf in df2.sort_values(by = 'doc_date', ascending = True)['pdf_file']:

                            merger.append(pdf)

                        merged_pdf = BytesIO()
                        merger.write(merged_pdf)
                        merger.close()

                        merged_pdf.seek(0)

                        merged_pdf_d[f'{store}_{platform}_commission_receipt'] = merged_pdf
                    
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                    
                    for i, df in enumerate([sale_df, commission_df1]):
                        excel_buffer = BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                            df.to_excel(writer, index=False, sheet_name="Sheet1")

                            # **Auto-adjust column width**
                            workbook = writer.book
                            worksheet = writer.sheets["Sheet1"]
                            for col_num, column in enumerate(df.columns):
                                max_length = max(df[column].astype(str).apply(len).max(), len(column))
                                worksheet.set_column(col_num, col_num, max_length)
                            
                        excel_buffer.seek(0)

                        zipf.writestr(f'รายงานภาษีขาย_{month}-{year}.xlsx' if i == 0 else f'รายงานภาษีซื้อ_{month}-{year}.xlsx', excel_buffer.read())

                    for key, value in merged_pdf_d.items():
                        zipf.writestr(f"{key}.pdf", value.read())

                zip_buffer.seek(0)


                st.markdown('<hr style="margin-top: 0px; margin-bottom: 0px;">', unsafe_allow_html=True)
                st.subheader('4. ดาวน์โหลดไฟล์')

                # Initialize session state for buttons
                if "form_submitted" not in st.session_state:
                    st.session_state.form_submitted = False  # Tracks form submission


                # **Only show form if calculation is completed**

                with st.form("my_form"):
                    st.write("📋 **กรอกข้อมูลเพื่อรับผลคำนวณ VAT**")

                    email_input = st.text_input("📧 Email", placeholder="your-email@email.com")
                    email_valid = True
                    if email_input:
                        if '@' not in email_input:
                            st.error('🚨 Email ผิด format (ต้องมี @)')
                            email_valid = False
                        elif email_input.split('@')[-1] not in ['gmail.com', 'yahoo.com', 'yahoo.co.th', 'outlook.com', 'hotmail.com', 'live.com']:
                            st.error('🚨 รองรับแค่ gmail, yahoo, outlook, hotmail, live')
                            email_valid = False
                    else:
                        email_valid = False  # Email is required

                    user_name = st.text_input("👤 ชื่อ")
                    user_surname = st.text_input("👤 นามสกุล")
                    
                    user_type = st.radio("📌 ประเภทผู้ใช้", ["บุคคลธรรมดา", "นิติบุคคล"], index=0, horizontal=True)
                    agree = st.checkbox("✅ ฉันยินยอมให้ใช้ข้อมูลเพื่อพัฒนาเครื่องมือคำนวณ VAT")

                    col1, col2, col3 = st.columns(3)
                    with col2:
                        submit_button = st.form_submit_button("📩 Submit", use_container_width=True)

                    # **Handle Form Submission**
                    if submit_button:
                        gdrive_credentials = json.loads(st.secrets["gdrive"]["GOOGLE_SHEETS_CREDENTIALS"])
                        scope = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets',"https://www.googleapis.com/auth/drive.file","https://www.googleapis.com/auth/drive"]
                        cerds = ServiceAccountCredentials.from_json_keyfile_dict(gdrive_credentials, scope)
                        client = gspread.authorize(cerds)
                        sheet = client.open("user_data").worksheet('vat_cal') # เป็นการเปิดไปยังหน้าชีตนั้นๆ

                        sheet.append_row([
                            'vat_cal', 
                            selected_month,
                            pd.to_datetime('today').strftime('%Y-%m-%d %H:%M:%S'),
                            user_type,
                            user_name, 
                            user_surname, 
                            ', '.join(store_name_ls),
                            email_input,
                            sale_df["vat"].sum()
                        ])
                        
                        if email_input.strip() and user_name.strip() and user_surname.strip() and agree:
                            st.session_state.form_submitted = True  # Mark form as submitted
                            st.success("✅ ข้อมูลถูกต้อง! ส่งอีเมล...")
                            # st.write([email_input, user_name, user_surname, user_type, agree])
                        else:
                            st.warning("⚠️ กรุณากรอกข้อมูลให้ครบถ้วนก่อนกด Submit!")

                    # # Gmail credentials
                        EMAIL_SENDER = st.secrets["email"]["EMAIL_SENDER"]
                        EMAIL_PASSWORD = st.secrets["email"]["EMAIL_PASSWORD"]  # Use App Password if 2FA is enabled

                        def send_email_with_zip_attachment(receiver_email, zip_buffer):
                            """Send an email with an in-memory Excel file containing the calculated DataFrame."""
                            try:
                                # Create email message
                                msg = EmailMessage()
                                msg["From"] = EMAIL_SENDER
                                msg["To"] = receiver_email,
                                msg["Subject"] = "VAT Calculation"
                                msg.set_content("Attached is your VAT calculation report.")

                                # Attach in-memory Excel file
                                msg.add_attachment(
                                    zip_buffer.read(),
                                    maintype="application",
                                    subtype="zip",
                                    filename="zip_file.zip"
                                )

                                # Send email via Gmail SMTP server
                                with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                                    server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                                    server.send_message(msg)

                                st.success(f"✅ Email sent to {receiver_email}")
                                return True

                            except Exception as e:
                                st.error(f"❌ Error: {e}")
                                return False

                        success = send_email_with_zip_attachment(receiver_email = email_input, zip_buffer=zip_buffer)
                    else:
                        st.success("📩 อีเมลของคุณถูกส่งเรียบร้อยแล้ว!")

                # download_col1, download_col2, doanload_col3 = st.columns([2, 1, 2])
                # with download_col2:
                #     st.download_button(
                #                 label = "download final file",
                #                 data = buffer,
                #                 file_name = f"ยอดคำนวณยื่นvat_{month}{year}.zip",
                #                 mime = "application/zip",
                #                 key="download_vat_button", 
                #                 use_container_width=True
                #         )


                

            else:
                #ปุ่ม calculate ยังไม่ถูก click
                pass
        else:
            st.warning('ปุ่มคำนวณจะแสดงหลังจากอัพโหลดไฟล์ยอดขายและไฟล์ค่าธรรมเนียมครบทุกไฟล์', icon = 'ℹ️')
    else:
        st.error('ใส่ชื่อร้านค้าที่ tab ด้านข้างให้ครบ', icon="🚨")
            

# %%
elif sidebar_radio == 'Q&A':
    st.header(f'💡 {sidebar_radio}', divider='grey')

    qa_df = pd.read_csv('qa.csv').sort_values(by = 'order', ascending = True).reset_index(drop = True)
    for i in range(qa_df.shape[0]):
        # st.write(i)
        q = qa_df.iloc[i, 1]
        a = qa_df.iloc[i, 2]
        # st.markdown(f'<h4>🟢 {q}?</h4>', unsafe_allow_html=True)
        with st.expander(q, icon = '📌'):
            st.write(a)
        # st.write('')
        st.write('')
        # st.subheader(f'{i + 1}. {q}?')
        # st.write(f'- {a}')
        # st.write('')
