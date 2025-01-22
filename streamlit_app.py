#%%
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import time
import datetime
import xlsxwriter
from io import BytesIO
from PyPDF2 import PdfMerger
import zipfile
import pypdf
import time
#%% sidebar
st.set_page_config(layout="wide")

with st.sidebar:
    st.subheader('เลือกจำนวนร้านค้าที่คุณมี')
    store_number = st.selectbox(
        label = 'เลือกจำนวนร้านค้าที่คุณมี', 
        options = [i for i in range(1, 4)],
        label_visibility = 'collapsed'
    )

    st.divider()

    st.subheader('ใส่ชื่อร้านค้า')
    store_name_ls = []
    for i in range(store_number):
        store_name = st.text_input(
            label = f'ชื่อร้านค่า #{i + 1}', 
            label_visibility = 'visible'
            )
        if store_name in store_name_ls and store_name != '':
            st.error('ชื่อร้านซ้ำ')
            break
        store_name_ls.append(store_name)

    st.divider()
    st.subheader('เลือกเมนูคำนวณ')
    sidebar_radio = st.radio(
        label = 'เลือกเมนูคำนวณ',
        options = ['เช็คว่าต้องจด VAT หรือยัง', 'คำนวณ VAT', 'วิธีใช้'], 
        index = 1, 
        label_visibility = 'collapsed'
    )
#%%
if sidebar_radio == 'เช็คว่าต้องจด VAT หรือยัง':

    st.write('')
    st.header(f'👍VAT cal: {sidebar_radio}')
    st.divider()
    st.subheader('1. เลือกปีที่ต้องการคำนวณ')
    selected_year = st.selectbox(
        label = "เลือกปีที่ต้องการคำนวณ",
        options = (str(pd.Timestamp.today().year), (str(pd.Timestamp.today().year - 1) + ' (เช็คว่าต้องจด vat ตั้งแต่ปีที่แล้วรึปล่าว)')), 
        label_visibility = 'collapsed'
    )
    selected_year = selected_year.split(' ')[0]
    current_time = pd.to_datetime('today') + pd.Timedelta(hours = 7)
    current_day = pd.to_datetime('today').day
    current_year = pd.to_datetime('today').year
    current_month = pd.to_datetime('today').month
    is_full_year = True if current_year - 1 == int(selected_year) else True if current_month == 12 and current_day == 31 else False

    ############################################################
    if len([store_name for store_name in store_name_ls if store_name != '']) == store_number:
        st.divider()
        st.subheader('2. เลือก platform ที่แต่ละร้านค้าทำการขายอยู่')
        # st.markdown(f'<h4>2. เลือก platform ที่แต่ละร้านค้าทำการขายอยู่</h4>', unsafe_allow_html=True)
        tick_cols = st.columns(store_number)

        for i, store_name in enumerate(store_name_ls):
            with tick_cols[i]:
                st.markdown(f'<h5>&emsp;✨ร้าน {store_name}</h5>', unsafe_allow_html=True)
                for platform in ['Shopee', 'Lazada', 'TikTok']:
                    st.checkbox(label=f'{platform}', value = True, key = 'tick_' + store_name + '_' + platform)
        
        ########################################################
        st.divider()
        st.subheader(f'3. upload files คำสั่งซื้อ (ข้อมูลปี {selected_year})')
        st.divider()
        for store_order, store_name in enumerate(store_name_ls):
            st.markdown(f'<h4>📍 3.{store_order + 1} ร้าน {store_name}</h4>', unsafe_allow_html=True)
            ###### part upload file ######
            platform_order = 0
            for platform in ['Shopee', 'Lazada', 'TikTok']:
                if st.session_state['tick_' + store_name + '_' + platform]: #
                    platform_order += 1
                    st.markdown(f'<h5>&ensp;&ensp;{"🟠 " if platform == "Shopee" else "🔵 " if platform == "Lazada" else "⚫ "} {platform}</h5>', unsafe_allow_html=True)

                    ################# upload shopee #################
                    if platform == 'Shopee': 
                        with st.expander("🔸ไฟล์คำสั่งซื้อของ Shopee โหลดที่ไหน ?"):
                            st.write('''
                                1. Log in เข้า Shopee Seller Center\n
                                2. เลือก "คำสั่งซื้อของฉัน"\n
                                3. เลือก "ทั้งหมด"\n
                                4. เลือก "ดาวน์โหลด"\n 
                                5. เลือกช่วงเวลา\n
                                \n
                                ** **หมายเหตุ**: ระบบของ Shopee ให้ดาวน์โหลดยอดขายได้ทีละ 1 เดือน แนะนำให้เลือก
                                ตั้งแต่วันที่ 1 จนถึงวันสุดท้ายของเดือน และทำการดาวน์โหลดข้อมูลของทุก
                                เดือนในปีที่ต้องการเช็คยอดว่าต้องจด vat แล้วหรือยัง
                            ''')

                        shopee_files = st.file_uploader(
                            label = f'upload ไฟล์ (.xlsx) ของทุกเดือนเข้ามาพร้อมกันได้เลย', 
                            accept_multiple_files = True,
                            type = 'xlsx', 
                            key = f'{store_name}_{platform}_raw_file'
                        )
                        if st.session_state[f'{store_name}_{platform}_raw_file'] != []:
                            st.success(f'สำเร็จ', icon="✅")
                        

                    ################# upload lazada #################
                    elif platform == 'Lazada':
                        with st.expander("🔹ไฟล์คำสั่งซื้อของ Lazada โหลดที่ไหน ?"):
                            st.write('''
                                1. Log in เข้า Lazada Seller Center
                                2. เลือก "คำสั่งซื้อ"\n
                                3. เลือก "ทั้งหมด"\n
                                4. ในช่อง "วันที่สั่งซื้อ" -> "กำหนดเอง" และเลือกช่วยเวลา (สามาถเลือกได้ทั้งปี)\n 
                                5. เลือก "Export" และเลือก "Export All"\n
                            ''')

                        lazada_file = st.file_uploader(
                            label = f'upload ไฟล์ (.xlsx) รองรับการอัพโหลดแค่ 1 ไฟล์', 
                            accept_multiple_files = False, 
                            type = 'xlsx',
                            key = f'{store_name}_{platform}_raw_file'
                        )
                        if lazada_file != None:
                            st.success(f'สำเร็จ', icon="✅")

                    elif platform == 'TikTok':    
                        with st.expander("▪️ ไฟล์คำสั่งซื้อของ TikTok โหลดที่ไหน ?"):
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
                            label = f'upload ไฟล์ (.csv) รองรับการอัพโหลดแค่ 1 ไฟล์', 
                            accept_multiple_files = False, 
                            type = 'csv',
                            key = f'{store_name}_{platform}_raw_file'
                        )   
                        if tiktok_file != None:
                            st.success(f'สำเร็จ', icon="✅")
                    
                    # st.markdown('##')
                    st.text("")
                    st.text("")
                    # st.markdown("***")

                else: #ไม่ได้ติ้ก platform นี้
                    pass

            st.divider()


        #show ปุ่มสำหรับกดคำนวณเมื่ออัพโหลดไฟล์สำเร็จ
        # check ว่า upload file ของ platform ยองแต่ละร้านที่ติ้กมาหมดแล้วรึยัง
        tick_ls = [key  for key, value in st.session_state.items() if 'tick' in key and value == True]
        check_d = {tick.replace('tick_', '')+'_raw_file': st.session_state[tick.replace('tick_', '')+'_raw_file'] for tick in tick_ls}

        if None in check_d.values(): 
            st.markdown("<h5 style='text-align: center'>upload file ให้เสร็จสิ้น เพื่อกดคำนวณ</g5>", unsafe_allow_html=True)
        else:
            col1, col2, col3 = st.columns(3)
            cont = False
            with col2:
                if st.button('คำนวณ', use_container_width = True):
                    total_sale = 0
                    df_dict = {}
                    cont = True


            if cont:          
                for key, value in st.session_state.items():
                    if 'raw_file' in key and 'Shopee' in key:
                        store = key.split('_')[0]
                        if store not in df_dict.keys():
                            df_dict[store] = {}

                        #shopee uploaded files are in list
                        df = pd.concat([pd.read_excel(f, converters = {'หมายเลขคำสั่งซื้อ': str}) for f in value], axis = 0)
                        
                        df = df[~df['สถานะการสั่งซื้อ'].isin(['ยกเลิกแล้ว'])].drop_duplicates()
                        df['year'] = pd.to_datetime(df['วันที่ทำการสั่งซื้อ'], format = '%Y-%m-%d %H:%M').dt.year #สำหรับตรวจว่า ปีของข้อมูลที่อัพโหลดมา ตรงกับปีที่เลือกไหม
                        df['month'] = pd.to_datetime(df['วันที่ทำการสั่งซื้อ'], format = '%Y-%m-%d %H:%M').dt.month #สำหรับตรวจว่าข้อมูลครบทุกเดือน

                        #check ว่าปีที่เลือก กับปีในไฟล์ตรงกัน
                        if df[df['year'].astype(int) != int(selected_year)].shape[0] != 0 and df[df['year'].astype(int) == int(selected_year)].shape[0] == 0: 
                            st.error(f'ข้อมูลร้านค้า {store} จาก Shopee: ปีที่เลือกคือปี {selected_year} / แต่มีแต่ข้อมูลของปี' + ', '.join(df['year'].astype(str).unique().tolist()) + '--> อาจเลือกไฟล์ผิด', icon="🚨")
                            cont = False
                            break
                        else:
                            if df[df['year'].astype(int) != int(selected_year)].shape[0] != 0:
                                st.warning(f'ข้อมูลร้านค้า {store} จาก Shopee มีข้อมูลของปี ' + ', '.join([y for y in df['year'].astype(str).unique().tolist() if y != selected_year]) +'ติดมาด้วย' + '--> กรุณาตรวจสอบ', icon="⚠️")
                            
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

                            #เตือนว่าข้อมูไม่ครบ
                            if missing_month_ls != []:
                                st.warning(f'โปรดเช็คว่าถูกต้องหรือไม่ ; ไฟล์ของร้าน {store} จาก Shopee ไม่มียอดขายในเดือนที่ในเดือนที่ {",".join(missing_month_ls)}', icon="⚠️")
                            
                            #screen out current month if current month != 1
                            if current_month == 1 and selected_year == current_year: #จะเกิดกรณีเมื่อ เลือกปีนี้ และเดือนนี้คือเดือนที่ 1
                                st.warning('เดือนนี้เดือน 1 แต่ยังไม่จบเดือน มีโอกาสที่สถานะคำสั่งซื้อจะยังเปลี่ยนแปลงเป็นยกเลิก', icon="ℹ️")

                                date_ls = sorted(pd.date_range(start = f'1/1/{selected_year}', end = current_time.strftime('%d/%m/%Y'), freq= 'D'))
                            else:
                                if selected_year == current_year: #ไม่ใช่เดือน 1 แล้ว แต่กำลังดูข้อมูลปี ปจบ
                                    st.info('เดือนนี้ยังไม่จบ ใช้ข้อมูลถึงแค่เดือนที่แล้วมาคำนวณ', icon="ℹ️")
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

                            total_sale += shopee_result_df[store+'_shopee']['order_value'].sum() + shopee_result_df[store+'_shopee']['shipping_value'].sum()

                            df_dict[store]['Shopee'] = shopee_result_df


                    elif 'raw_file' in key and 'Lazada' in key:
                        store = key.split('_')[0]
                        if store not in df_dict.keys():
                            df_dict[store] = {}

                        df = pd.read_excel(value, converters={'orderNumber':str})
                        df = df[~df['status'].isin(['canceled', 'returned', 'Package Returned'])]

                        df['year'] = pd.to_datetime(df['createTime'], format = '%d %b %Y %H:%M').dt.year #สำหรับตรวจว่า ปีของข้อมูลที่อัพโหลดมา ตรงกับปีที่เลือกไหม
                        df['month'] = pd.to_datetime(df['createTime'], format = '%d %b %Y %H:%M').dt.month #สำหรับตรวจว่าข้อมูลครบทุกเดือน

                        #check ว่าปีที่เลือก กับปีในไฟล์ตรงกัน
                        if df[df['year'].astype(int) != int(selected_year)].shape[0] != 0 and df[df['year'].astype(int) == int(selected_year)].shape[0] == 0: 
                            st.error(f'ข้อมูลร้านค้า {store} ของ Lazada: ปีที่เลือกคือปี {selected_year} / แต่มีแต่ข้อมูลของปี' + ', '.join(df['year'].astype(str).unique().tolist()) + '--> อาจเลือกไฟล์ผิด', icon="🚨")
                            break
                        else:
                            if df[df['year'].astype(int) != int(selected_year)].shape[0] != 0:
                                st.warning(f'ข้อมูลร้านค้า {store} จาก Lazada มีข้อมูลของปี ' + ', '.join([y for y in df['year'].astype(str).unique().tolist() if y != selected_year]) +'ติดมาด้วย' + '--> กรุณาตรวจสอบ', icon="⚠️")

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

                            #เตือนว่าข้อมูไม่ครบ
                            if missing_month_ls != []:
                                st.warning(f'โปรดเช็คว่าถูกต้องหรือไม่ ; ไฟล์ของร้าน {store} จาก Lazada ไม่มียอดขายในเดือนที่ในเดือนที่ {",".join(missing_month_ls)}', icon="⚠️")
                            
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
                                st.dataframe(df[df['status'] != 'confirmed'])
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

                            total_sale += lazada_result_df[store+'_lazada']['order_value'].sum() + lazada_result_df[store+'_lazada']['shipping_value'].sum()

                            df_dict[store]['Lazada'] = lazada_result_df
                    
                    elif 'raw_file' in key and 'TikTok' in key:
                        store = key.split('_')[0]
                        if store not in df_dict.keys():
                            df_dict[store] = {}

                        df = pd.read_csv(value, converters={'Order ID':str})
                        df = df[df['Order Status'] != 'Canceled'].drop_duplicates().reset_index(drop = True)

                        df['year'] = pd.to_datetime(df['Created Time'], format = '%d/%m/%Y %H:%M:%S\t').dt.year #สำหรับตรวจว่า ปีของข้อมูลที่อัพโหลดมา ตรงกับปีที่เลือกไหม
                        df['month'] = pd.to_datetime(df['Created Time'], format = '%d/%m/%Y %H:%M:%S\t').dt.month #สำหรับตรวจว่าข้อมูลครบทุกเดือน

                        #check ว่าปีที่เลือก กับปีในไฟล์ตรงกัน
                        if df[df['year'].astype(int) != int(selected_year)].shape[0] != 0 and df[df['year'].astype(int) == int(selected_year)].shape[0] == 0: 
                            st.error(f'ข้อมูลร้านค้า {store} จาก TikTok: ปีที่เลือกคือปี {selected_year} / แต่มีแต่ข้อมูลของปี' + ', '.join(df['year'].astype(str).unique().tolist()) + '--> อาจเลือกไฟล์ผิด', icon="🚨")
                            break
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
                                st.warning(f'โปรดเช็คว่าถูกต้องหรือไม่ ; ไฟล์ของร้าน {store} จาก TikTok ไม่มียอดขายในเดือนที่ในเดือนที่ {", ".join(missing_month_ls)}', icon="⚠️")
                            
                            #screen out current month if current month != 1
                            if current_month == 1 and selected_year == current_year: #จะเกิดกรณีเมื่อ เลือกปีนี้ และเดือนนี้คือเดือนที่ 1
                                st.warning('เดือนนี้เดือน 1 แต่ยังไม่จบเดือน มีโอกาสที่สถานะคำสั่งซื้อจะยังเปลี่ยนแปลงอยู่นะ', icon="ℹ️")

                                date_ls = sorted(pd.date_range(start = f'1/1/{selected_year}', end = current_time.strftime('%d/%m/%Y'), freq= 'D'))
                                st.write(date_ls)
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

                            total_sale += tiktok_result_df[store+'_tiktok']['order_value'].sum() + tiktok_result_df[store+'_tiktok']['shipping_value'].sum()

                            df_dict[store]['TikTok'] = tiktok_result_df

                
                st.divider()
                result_df = pd.DataFrame()
                for store_name, store_dict in df_dict.items():
                    for platform in ['Shopee', 'Lazada', 'TikTok']:
                        if platform in store_dict.keys():
                            df = store_dict[platform]
                            result_df = pd.concat([result_df, df], axis = 1)
                
                result_df['sum'] = result_df.sum(axis = 1)
                result_df['cumsum'] = result_df['sum'].cumsum()

                if result_df[result_df['cumsum'] >= 1800000].shape[0] > 0:
                    st.write(f'ยอดขายรวมในปีที่เลือก ({selected_year}) = {"{:,.2f}".format(result_df.iloc[result_df.shape[0] - 1, -1])} THB')
                    st.write(f'ยอดขายถึง 1.8 m ตั้งแต่วันที่ {result_df[result_df["cumsum"] >= 1800000].index[0]}')
                    
                else:
                    st.write(f'ยอดขายรวมในปี {selected_year} = {"{:.2f}".format(result_df.iloc[result_df.shape[0] - 1, -1])} THB --> ยังไม่ต้องจด vat')

                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    result_df.to_excel(writer, sheet_name='Sheet1')
                    # writer.save()
                processed_data = output.getvalue()


                col1, col2, col3 = st.columns(3)
                with col2:
                    st.download_button(
                        label = f"Download ไฟล์สรุปยอดขายรวมของปี {selected_year}",
                        data = processed_data,
                        file_name = f"ไฟล์สรุปยอดขายรวม_{selected_year}.xlsx",
                        mime = "application/vnd.ms-excel",
                        key = "download_button" 
                    )

    else:
        st.error('กรูณาใส่ชื่อร้านค้าที่ tab ด้านข้างให้ครบ', icon="🚨")

elif sidebar_radio == 'คำนวณ VAT':
    

    st.write('')
    st.header(f'👍VAT cal: {sidebar_radio}')
    st.divider()

    st.subheader('1. เลือกเดือนที่ต้องการคำนวณ VAT')
    selected_month = st.selectbox(
        label = 'select_month', 
        options = ([(pd.to_datetime('today').replace(day = 1) - pd.DateOffset(months = i)).strftime('%b, %Y') for i in range(1, 7)]), 
        index = 0, 
        label_visibility = 'collapsed'
    )
    month = pd.to_datetime(selected_month.split(', ')[0], format = '%b').month
    year = pd.to_datetime(selected_month.split(', ')[1], format = '%Y').year

    if len([store_name for store_name in store_name_ls if store_name != '']) == store_number:
        st.divider()
        st.subheader('2. เลือก platform ที่แต่ละร้านค้าทำการขายอยู่')
        # st.markdown(f'<h4>2. เลือก platform ที่แต่ละร้านค้าทำการขายอยู่</h4>', unsafe_allow_html=True)
        tick_cols = st.columns(store_number)

        for i, store_name in enumerate(store_name_ls):
            with tick_cols[i]:
                st.markdown(f'<h5>&emsp;✨ร้าน {store_name}</h5>', unsafe_allow_html=True)
                for platform in ['Shopee', 'Lazada', 'TikTok']:
                    st.checkbox(label=f'{platform}', value = True, key = 'tick_' + store_name + '_' + platform)
    

        st.divider()
        st.subheader(f'3. upload files คำสั่งซื้อและใบเสร็จค่าธรรมเนียมของเดือน {month}-{year}')

        for store_order, store_name in enumerate(store_name_ls):
            st.markdown(f'<h4>📍 3.{store_order + 1} ร้าน {store_name}</h4>', unsafe_allow_html=True)
            ###### part upload file ######
            platform_order = 0
            for platform in ['Shopee', 'Lazada', 'TikTok']:
                if st.session_state['tick_' + store_name + '_' + platform]: #if shopee of the store is ticked
                    platform_order += 1
                    if platform == 'Shopee': 
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            st.markdown(f'<h5>&ensp;&ensp;🟠 ไฟล์คำสั่งซื้อ {platform}</h5>', unsafe_allow_html=True)
                            with st.expander("🔸ไฟล์คำสั่งซื้อของ Shopee โหลดที่ไหน ?"):
                                st.write('''
                                    The chart above shows some numbers I picked for you.
                                    I rolled actual dice for these, so they're *guaranteed* to
                                    be random.
                                ''')

                            shopee_sale_file = st.file_uploader(
                                label = f'upload ไฟล์ยอดขาย (.xlsx)', 
                                accept_multiple_files = False,
                                type = 'xlsx', 
                                key = f'{store_name}_{platform}_sale_raw_file'
                            )


                            if shopee_sale_file != None:
                                st.success(f'สำเร็จ', icon="✅")

                        with col2:
                            st.markdown(f'<h5>&ensp;&ensp;🟠 ค่าธรรมเนียม {platform}</h5>', unsafe_allow_html=True)
                            with st.expander("🔸ไฟล์ใบเสร็จค่าธรรมเนียม Shopee โหลดที่ไหน ?"):
                                st.write('''
                                    The chart above shows some numbers I picked for you.
                                    I rolled actual dice for these, so they're *guaranteed* to
                                    be random.
                                ''')

                            shopee_commission_file = st.file_uploader(
                                label = f'upload file ใบเสร็จค่าธรรมเนียม (.zip)', 
                                accept_multiple_files = False,
                                type = 'zip', 
                                key = f'{store_name}_{platform}_commission_raw_file'
                            )


                            if shopee_commission_file != None:
                                st.success(f'สำเร็จ', icon="✅")
                        
                        

                    elif platform == 'Lazada':
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f'<h5>&ensp;&ensp;🔵 ยอดขาย {platform} </h5>', unsafe_allow_html=True)
                            with st.expander("🔹ไฟล์คำสั่งซื้อของ Lazada โหลดที่ไหน ?"):
                                st.write('''
                                    The chart above shows some numbers I picked for you.
                                    I rolled actual dice for these, so they're *guaranteed* to
                                    be random.
                                ''')
                            
                            lazada_sale_file = st.file_uploader(
                                label = f'upload ไฟล์ยอดขาย (.xlsx)', 
                                accept_multiple_files = False, 
                                type = 'xlsx',
                                key = f'{store_name}_{platform}_sale_raw_file'
                                )
                            if lazada_sale_file != None:
                                st.success(f'สำเร็จ', icon="✅")

                        with col2:
                            st.markdown(f'<h5>&ensp;&ensp;🔵 ค่าธรรมเนียม {platform}</h5>', unsafe_allow_html=True)
                            with st.expander("🔹ไฟล์ใบเสร็จค่าธรรมเนียม Lazada โหลดที่ไหน ?"):
                                st.write('''
                                    The chart above shows some numbers I picked for you.
                                    I rolled actual dice for these, so they're *guaranteed* to
                                    be random.
                                ''')

                            lazada_commission_files = st.file_uploader(
                                label = f'upload ไฟล์ (.pdf) ทุกรายการเข้ามาพร้อมกันได้เลย', 
                                accept_multiple_files = True, 
                                type = 'pdf',
                                key = f'{store_name}_{platform}_commission_raw_file'
                                )
                            if st.session_state[f'{store_name}_{platform}_commission_raw_file'] != []:
                                st.success(f'สำเร็จ', icon="✅")

                    elif platform == 'TikTok':
                        col1, col2 = st.columns(2)

                        with col1:
                            st.markdown(f'<h5>&ensp;&ensp;⚫ ยอดขาย {platform}</h5>', unsafe_allow_html=True)
                            with st.expander("▪️ไฟล์คำสั่งซื้อของ TikTok โหลดที่ไหน ?"):
                                st.write('''
                                    The chart above shows some numbers I picked for you.
                                    I rolled actual dice for these, so they're *guaranteed* to
                                    be random.
                                ''')
                            tiktok_sale_file = st.file_uploader(
                                label = f'upload ไฟล์ยอดขาย (.csv)', 
                                accept_multiple_files = False, 
                                type = 'csv', 
                                key = f'{store_name}_{platform}_sale_raw_file'
                                )
                            if tiktok_sale_file != None:
                                st.success(f'สำเร็จ', icon="✅")

                        with col2:
                            st.markdown(f'<h5>&ensp;&ensp;⚫ ค่าธรรมเนียม {platform}</h5>', unsafe_allow_html=True)
                            with st.expander("▪️ไฟล์ใบเสร็จค่าธรรมเนียม TikTok โหลดที่ไหน ?"):
                                st.write('''
                                    The chart above shows some numbers I picked for you.
                                    I rolled actual dice for these, so they're *guaranteed* to
                                    be random.
                                ''')
                            tiktok_commission_file = st.file_uploader(
                            label = f'upload file ใบเสร็จค่าธรรมเนียม (.zip)', 
                            accept_multiple_files = False, 
                            type = 'zip', 
                            key = f'{store_name}_{platform}_commission_raw_file'
                            )
                            if tiktok_commission_file != None:
                                st.success(f'สำเร็จ', icon="✅")
                    
                    st.write("")
                    st.write("")
                    
                else:
                    pass
            
            st.divider()
        
        #show ปุ่มสำหรับกดคำนวณเมื่ออัพโหลดไฟล์สำเร็จ
        # check ว่า upload file ของ platform ยองแต่ละร้านที่ติ้กมาหมดแล้วรึยัง
        tick_ls = [key  for key, value in st.session_state.items() if 'tick' in key and value == True]

        # st.write(st.session_state)
        check_d1 = {tick.replace('tick_', '')+'_commission_raw_file': st.session_state[tick.replace('tick_', '')+'_commission_raw_file'] for tick in tick_ls}
        check_d2 = {tick.replace('tick_', '')+'_sale_raw_file': st.session_state[tick.replace('tick_', '')+'_sale_raw_file'] for tick in tick_ls}
        # st.write(check_d1)
        # st.write(check_d2)
        check_d = {}

        for key,value in check_d1.items():
            check_d[key] = value
        for key,value in check_d2.items():
            check_d[key] = value

        if check_d == None:
            check_d = {"aa": None}

        if None in check_d.values() or [] in check_d.values(): 
            st.write('please upload all files')
        else:
            if st.button('calculate', ):
                sale_d = {}
                commission_d = {}

                for key, value in st.session_state.items(): #value = uploaded zip file
                    ############## sale ##############
                    if '_sale_raw_file' in key and 'Shopee' in key:
                        store = key.split('_')[0]
                        if store not in sale_d.keys():
                            sale_d[store] = {}

                        df = pd.read_excel(value, converters={'หมายเลขคำสั่งซื้อ':str})
                        df = df[~df['สถานะการสั่งซื้อ'].isin(['ยกเลิกแล้ว'])].drop_duplicates()

                        df['year'] = pd.to_datetime(df['วันที่ทำการสั่งซื้อ'], format = '%Y-%m-%d %H:%M').dt.year #สำหรับตรวจว่า ปีของข้อมูลที่อัพโหลดมา ตรงกับปีที่เลือกไหม
                        df['month'] = pd.to_datetime(df['วันที่ทำการสั่งซื้อ'], format = '%Y-%m-%d %H:%M').dt.month #สำหรับตรวจว่าข้อมูลครบทุกเดือน

                        #check ว่าปีที่เลือก กับปีในไฟล์ตรงกัน
                        if df[df['year'].astype(int) != int(year)].shape[0] != 0 and df[df['year'].astype(int) == int(year)].shape[0] == 0: 
                            st.error(f'ข้อมูลร้านค้า {store} จาก Shopee: ปีที่เลือกคือเดือน {month}/{year} แต่ไม่มีข้อมูลของเดือนนี้' + '--> อาจเลือกไฟล์ผิด', icon="🚨")
                            break
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
                            df = df[['สถานะการสั่งซื้อ', 'วันที่ทำการสั่งซื้อ', 'หมายเลขคำสั่งซื้อ', 'ชื่อผู้ใช้ (ผู้ซื้อ)', 'ราคาขายสุทธิ', 'โค้ดส่วนลดชำระโดยผู้ขาย', 
                                                            'ค่าจัดส่งที่ชำระโดยผู้ซื้อ', 'ค่าจัดส่งที่ Shopee ออกให้โดยประมาณ', 'ค่าจัดส่งสินค้าคืน', 'ค่าจัดส่งโดยประมาณ']]

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

                                sale_ls.append(['Shopee', store_name, 'สินค้า', order_date, status, order_no, customer_name, before_vat, vat, include_vat])

                                shipping_fee_from_buyer = df1.loc[0, 'ค่าจัดส่งที่ชำระโดยผู้ซื้อ']
                                if float(shipping_fee_from_buyer) != 0:
                                    shipping_vat = round((shipping_fee_from_buyer * 0.07) / 1.07, 2)
                                    shipping_before_vat = shipping_fee_from_buyer - shipping_vat
                                    sale_ls.append(['Shopee', store_name, 'บริการ', order_date, status, order_no, customer_name, shipping_before_vat, shipping_vat, shipping_fee_from_buyer])

                            shopee_sale_df_result = pd.DataFrame(sale_ls, columns = ['platform', 'store_name', 'type', 'order_date', 'status', 'order_no', 'customer_name', 'before_vat', 'vat', 'include_vat'])
                            shopee_sale_df_result = shopee_sale_df_result[['platform', 'store_name', 'type', 'order_date', 'status', 'order_no', 'customer_name', 'before_vat', 'vat', 'include_vat']]


                            sale_d[store]['shopee'] = shopee_sale_df_result

                    elif '_sale_raw_file' in key and 'Lazada' in key:
                        store = key.split('_')[0]
                        if store not in sale_d.keys():
                            sale_d[store] = {}

                        df = pd.read_excel(value, converters={'orderNumber':str})
                        df = df[~df['status'].isin(['canceled', 'returned', 'Package Returned'])].drop_duplicates().reset_index(drop = True)

                        df['year'] = pd.to_datetime(df['createTime'], format = '%d %b %Y %H:%M').dt.year #สำหรับตรวจว่า ปีของข้อมูลที่อัพโหลดมา ตรงกับปีที่เลือกไหม
                        df['month'] = pd.to_datetime(df['createTime'], format = '%d %b %Y %H:%M').dt.month #สำหรับตรวจว่าข้อมูลครบทุกเดือน

                        #check ว่าปีที่เลือก กับปีในไฟล์ตรงกัน
                        if df[df['year'].astype(int) != int(year)].shape[0] != 0 and df[df['year'].astype(int) == int(year)].shape[0] == 0: 
                            st.error(f'ข้อมูลร้านค้า {store} จาก Lazada: ปีที่เลือกคือปี {year} / แต่มีแต่ข้อมูลของปี' + ', '.join(df['year'].astype(str).unique().tolist()) + '--> อาจเลือกไฟล์ผิด', icon="🚨")
                            break
                        else:
                            if df[(df['year'].astype(int) != int(year)) & (df['month'].astype(int) != int(month))].shape[0] != 0:
                                st.warning(f'ข้อมูลร้านค้า {store} จาก Lazada: ปีที่เลือกคือเดือน {month}/{year} มีข้อมูลของเดือนอื่นติดมาด้วย' + '--> กรุณาตรวจสอบ', icon="⚠️")

                            #screen out year
                            df = df[(df['year'] == int(year)) & (df['month'] == month)].reset_index(drop = True)

                            uncompleted_order_count = len(df[df['status'] != 'confirmed']['status'].unique().tolist())
                            if uncompleted_order_count != 0:
                                st.warning(f"ไฟล์ของร้าน {store} (Lazada) ยังมีคำสั่งซื้อที่ยังไม่สำเร็จอยู่ {uncompleted_order_count} รายการ --> อาจทำให้ค่ารายได้รวมเปลี่ยนแปลงได้หากมีการยกเลิกคำสั่งซื้อ", icon="⚠️")
                                st.dataframe(df[df['status'] != 'confirmed'])
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

                            sale_ls.append(['Lazada', store_name, 'สินค้า', order_date, status, order_no, customer_name, before_vat, vat, include_vat])

                        lazada_sale_df_result = pd.DataFrame(sale_ls, columns = ['platform', 'store_name', 'type', 'order_date', 'status', 'order_no', 'customer_name', 'before_vat', 'vat', 'include_vat'])
                        lazada_sale_df_result = lazada_sale_df_result[['platform', 'store_name', 'type', 'order_date', 'status', 'order_no', 'customer_name', 'before_vat', 'vat', 'include_vat']]

                        sale_d[store]['shopee'] = lazada_sale_df_result

                    elif '_sale_raw_file' in key and 'TikTok' in key:
                        store = key.split('_')[0]
                        if store not in sale_d.keys():
                            sale_d[store] = {}

                        df = pd.read_csv(value, converters={'Order ID':str})

                        df = df[~df['Order Status'].isin(['Canceled'])]
                        df = df[df['Order Status'] != 'Canceled'].drop_duplicates().reset_index(drop = True)

                        df['year'] = pd.to_datetime(df['Created Time'], format = '%d/%m/%Y %H:%M:%S\t').dt.year #สำหรับตรวจว่า ปีของข้อมูลที่อัพโหลดมา ตรงกับปีที่เลือกไหม
                        df['month'] = pd.to_datetime(df['Created Time'], format = '%d/%m/%Y %H:%M:%S\t').dt.month #สำหรับตรวจว่าข้อมูลครบทุกเดือน

                        #check ว่าปีที่เลือก กับปีในไฟล์ตรงกัน
                        if df[df['year'].astype(int) != int(year)].shape[0] != 0 and df[df['year'].astype(int) == int(year)].shape[0] == 0: 
                            st.error(f'ข้อมูลร้านค้า {store} | TikTok: ปีที่เลือกคือปี {year} / แต่มีแต่ข้อมูลของปี' + ', '.join(df['year'].astype(str).unique().tolist()) + '--> อาจเลือกไฟล์ผิด', icon="🚨")
                            break
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

                            sale_ls.append(['TikTok', store_name, 'สินค้า', order_date, status, order_no, customer_name, before_vat, vat, include_vat])


                            shipping_fee_from_buyer = df1.loc[0, 'Shipping Fee After Discount']

                            if float(shipping_fee_from_buyer) != 0:
                                shipping_vat = round((shipping_fee_from_buyer * 0.07) / 1.07, 2)
                                shipping_before_vat = shipping_fee_from_buyer - shipping_vat
                                sale_ls.append(['TikTok', store_name, 'บริการ', order_date, status, order_no, customer_name, shipping_before_vat, shipping_vat, shipping_fee_from_buyer])


                        tiktok_sale_df_result = pd.DataFrame(sale_ls, columns = ['platform', 'store_name', 'type', 'order_date', 'status', 'order_no', 'customer_name', 'before_vat', 'vat', 'include_vat'])
                        tiktok_sale_df_result = tiktok_sale_df_result[['platform', 'store_name', 'type', 'order_date', 'status', 'order_no', 'customer_name', 'before_vat', 'vat', 'include_vat']]

                        sale_d[store]['TikTok'] = tiktok_sale_df_result

                    ############## sale ##############
                    if '_commission_raw_file' in key and 'Shopee' in key:
                        ls = []
                        pdf_ls = []
                        store = key.split('_')[0]

                        if store not in commission_d.keys():
                            commission_d[store] = {}

                        with zipfile.ZipFile(value, 'r') as z:
                            sorted_file_ls = ['-'.join(ls) for ls in sorted([n.split('-') for n in z.namelist() if 'SPX' not in n], key = lambda x: int(x[4]))]
                            progress_bar = st.progress(0, text = 'processing shopee commission pdf')
                            
                            for i, file_name in enumerate(sorted_file_ls):
                                if 'SPX' in file_name:
                                    progress_bar.progress((i + 1) / len(sorted_file_ls), text='reading shopee commission pdf files')
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
                                            company_tax_id = text.split('Tax ID ')[-1].split('เลขที่/')[0]
                                        elif 'after discount' in text:
                                            before_vat = round(float(text.split(' ')[-1].replace(',', '')), 2)
                                        elif 'VAT' in text and '7%' in text:
                                            vat = round(float(text.split(' ')[-1].replace(',', '')), 2)
                                        elif 'Customer name' in text:
                                            company_name = text.split('Customer name ')[-1]
                                                    
                                if None in [doc_date, company_name, company_tax_id, issued_company, doc_num, before_vat, vat]:
                                    st.error(f'something wrong with {store} Shopee commission file: {file_name}', icon="🚨")
                                    break
                                else:
                                    ls.append([doc_date, company_name, company_tax_id, issued_company, doc_num, before_vat, vat])
                                    pdf_ls.append([company_name, 'Shopee', doc_date, BytesIO(z.read(file_name))])
                                    progress_bar.progress((i + 1) / len(sorted_file_ls), text = f'reading {store} Shopee commission files')

                        commission_d[store]['shopee'] = {
                            'commission_df': pd.DataFrame(ls, columns = ['doc_date', 'company_name', 'company_tax_id', 'issue_comapny', 'doc_num', 'before_vat', 'vat']), 
                            'pdf_df': pd.DataFrame(pdf_ls, columns = ['company_name', 'platform', 'doc_date', 'pdf_file'])
                        }
                        progress_bar.empty()


                    elif '_commission_raw_file' in key and 'Lazada' in key:
                        ls = []
                        pdf_ls = []
                        store = key.split('_')[0]
                        doc_num_ls = []

                        if store not in commission_d.keys():
                            commission_d[store] = {}

                        progress_bar = st.progress(0, text = 'processing Lazada commission pdf')
                        for file_order, file_name in enumerate(lazada_commission_files):
                            pdf_file = pypdf.PdfReader(file_name)


                            if 'Lazada Express Limited' in pdf_file.pages[0].extract_text() or 'Shipping Fee' in pdf_file.pages[0].extract_text():
                                progress_bar.progress((i + 1) / len(lazada_commission_files), text = 'reading Lazada commission pdf files')
                            elif doc_num in doc_num_ls: #ไฟล์ที่อ่าน มีเลขเอกสารซ้ำ น่าจะเพราะอัพโหลดมาซ้ำ
                                progress_bar.progress((file_order + 1) / len(lazada_commission_files), text = 'reading Lazada commission pdf files')
                            else:
                                doc_date, doc_num, issued_company, before_vat, vat, company_name, company_tax_id = None, None, None, None, None, None, None
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
                                        company_name = pdf_file.pages[0].extract_text().split('\n')[i + 2].replace('  ', ' ')
                                        company_tax_id = pdf_file.pages[0].extract_text().split('\n')[i + 7].split('Tax ID: ')[-1].split('Invoice')[0]

                                if None in [doc_date, company_name, company_tax_id, issued_company, doc_num, before_vat, vat]:
                                    st.error(f'something wrong with {store} Lazada commission file: {file_name}', icon="🚨")
                                    break
                                else:
                                    ls.append([doc_date, company_name, company_tax_id, issued_company, doc_num, before_vat, vat])
                                    pdf_ls.append([company_name, 'Lazada', doc_date, pdf_file])
                                    doc_num_ls.append(doc_num) #เอามากัน กรณีคนอัพโหลดไฟล์มาซ้ำ
                                    progress_bar.progress((i + 1) / len(lazada_commission_files), text = f'reading {store} Shopee commission files')

                        commission_d[store]['lazada'] = {
                            'commission_df': pd.DataFrame(ls, columns = ['doc_date', 'company_name', 'company_tax_id', 'issue_comapny', 'doc_num', 'before_vat', 'vat']), 
                            'pdf_df': pd.DataFrame(pdf_ls, columns = ['company_name', 'platform', 'doc_date', 'pdf_file'])
                        }
                        progress_bar.empty()
                        

                    elif '_commission_raw_file' in key and 'TikTok' in key:
                        ls = []
                        pdf_ls = []
                        store = key.split('_')[0]

                        if store not in commission_d.keys():
                            commission_d[store] = {}

                        progress_bar = st.progress(0, text = 'processing TikTok commission pdf')
                        with zipfile.ZipFile(value,'r') as z:
                            sorted_file_ls = sorted([n for n in z.namelist() if 'THJV' not in n and 'TTSTHAC' not in n])
                            progress_bar = st.progress(0, text = 'processing tiktok commission pdf')

                            for i, file_name in enumerate(sorted_file_ls):
                                if 'THJV' in file_name or 'TTSTHAC' in file_name:
                                    progress_bar.progress((i + 1) / len(sorted_file_ls), text='reading tiktok commission pdf files')
                                else:
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
                                        st.error(f'something wrong with {store} TikTok commission file: {file_name}', icon="🚨")
                                        break
                                    else:
                                        ls.append([doc_date, company_name, company_tax_id, issued_company, doc_num, before_vat, vat])
                                        pdf_ls.append([company_name, 'TikTok', doc_date, pdf_file])
                                        progress_bar.progress((i + 1) / len(sorted_file_ls), text = f'reading {store} Shopee commission files')
                            
                            commission_d[store]['tiktok'] = {
                                    'commission_df': pd.DataFrame(ls, columns = ['doc_date', 'company_name', 'company_tax_id', 'issue_comapny', 'doc_num', 'before_vat', 'vat']), 
                                    'pdf_df': pd.DataFrame(pdf_ls, columns = ['company_name', 'platform', 'doc_date', 'pdf_file'])
                                }
                            progress_bar.empty()

                ############## merge data ##############  
                sale_df = pd.DataFrame()
                for store in store_name_ls:
                    for platform in ['shopee', 'lazada', 'tiktok']:
                        if platform in sale_d[store].keys():
                            sale_df = pd.concat([sale_df, sale_d[store][platform]])

                
                commission_df = pd.DataFrame()
                for store in store_name_ls:
                    for platform in ['shopee', 'lazada', 'tiktok']:
                        if platform in commission_d[store].keys():
                            commission_df = pd.concat([commission_df, commission_d[store][platform]['commission_df']])
                st.dataframe(commission_df)


                if len(commission_df['company_tax_id'].str.lower().str.replace(' ', '').unique()) >= 2:
                    st.subheader('5. check')
                    st.warning('เจอชื่อ บ ในใบเสร็จ มากกว่า 1 ชื่อ --> กรุณาเลือกชื่อผู้จ่าย vat ที่ถูกต้อง', icon="⚠️")


                    for i, tax_id in enumerate(commission_df['company_tax_id'].str.replace(' ', '').unique().tolist()):
                        # show_name = commission_df[commission_df['company_name1'] == name]['company_name'].tolist()[0]
                        name = commission_df[commission_df['company_tax_id'].str.replace(' ', '') == tax_id].reset_index(drop = True).loc[0, 'company_name']
                        st.checkbox(label=f'{name}', key = f'tax_id_{tax_id}')
                        st.write(st.session_state)
                        st.dataframe(commission_df[commission_df['company_tax_id'] == tax_id])

                    commission_df1 = pd.DataFrame()
                    for i, tax_id in enumerate([key for key in st.session_state.keys() if 'tax_id' in key]):
                        if st.session_state[f'tax_id_{tax_id}']:
                            commission_df1 = pd.concat([commission_df1, commission_df[commission_df['company_tax_id'] == tax_id]], axis = 0).reset_index(drop = True)

                    # commission_df = commission_df1

                    if st.button('finish ticking'):
                        ready_to_download = True
                    else:
                        ready_to_download = False


                else:
                    ready_to_download = True
                    st.divider()

                
                if ready_to_download:
                    st.write(f'ภาษีมูลค่าเพิ่มขาย = {sale_df["vat"].sum()}')
                    st.write(f'ภาษีมูลค่าเพิ่มซื้อ = {commission_df["vat"].sum()}')
                    st.write(f'ภาษีมูลค่าเพิ่มที่ต้องจ่ายสรรพากร = {sale_df["vat"].sum() - commission_df["vat"].sum()}')
                    
                    merged_pdf_d = {}
                    for store, d1 in commission_d.items():
                        for platform, d2 in d1.items():
                            pdf_df = d2['pdf_df'].sort_values(by = 'doc_date', ascending = True).reset_index(drop = True)

                            merger = PdfMerger()

                            for i in range(pdf_df.shape[0]):
                                merger.append(pdf_df.loc[i, 'pdf_file'])

                            merged_pdf = BytesIO()
                            merger.write(merged_pdf)
                            merger.close()

                            merged_pdf.seek(0)

                            merged_pdf_d[f'{store}_{platform}_commission_receipt'] = merged_pdf
                
                    buffer = BytesIO()
                    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                        
                        for i, df in enumerate([sale_df, commission_df]):
                            excel_buffer = BytesIO()
                            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                                df.to_excel(writer, index=False, sheet_name="Sheet1")
                            excel_buffer.seek(0)

                            zipf.writestr(f'รายงานภาษีขาย_{month}{year}.xlsx' if i == 0 else f'รายงานภาษีซื้อ_{month}{year}.xlsx', excel_buffer.getvalue())

                        for key, value in merged_pdf_d.items():
                            zipf.writestr(f"{key}.pdf", value.read())

                    
                    st.download_button(
                                label = "download final file",
                                data = buffer,
                                file_name = f"ยอดคำนวณยื่นvat_{month}{year}.zip",
                                mime = "application/zip",
                                key="download_vat_button" 
                        )
                            


    
elif sidebar_radio == 'วิธีใช้':
    pass

# %%
