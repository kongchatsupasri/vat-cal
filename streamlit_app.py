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
#%% function

####################################### sale #######################################
#กรณีที่่เอกสารอยู่นอกเดือนที่เลือกมา
@st.cache_data
def shopee_sale_df(file, store_name):
    shopee_sale_df = pd.read_excel(file, converters={'หมายเลขคำสั่งซื้อ':str})
    shopee_sale_df = shopee_sale_df[~shopee_sale_df['สถานะการสั่งซื้อ'].isin(['ยกเลิกแล้ว', 'ยังไม่ชำระ'])]
    shopee_sale_df['วันที่ทำการสั่งซื้อ'] = pd.to_datetime(shopee_sale_df['วันที่ทำการสั่งซื้อ'], format = '%Y-%m-%d %H:%M').dt.date
    # shopee_sale_df['หมายเลขคำสั่งซื้อ'] = shopee_sale_df['หมายเลขคำสั่งซื้อ'].astype(str)
    shopee_sale_df = shopee_sale_df[['สถานะการสั่งซื้อ', 'วันที่ทำการสั่งซื้อ', 'หมายเลขคำสั่งซื้อ', 'ชื่อผู้ใช้ (ผู้ซื้อ)', 'ราคาขายสุทธิ', 'โค้ดส่วนลดชำระโดยผู้ขาย', 
                                    'ค่าจัดส่งที่ชำระโดยผู้ซื้อ', 'ค่าจัดส่งที่ Shopee ออกให้โดยประมาณ', 'ค่าจัดส่งสินค้าคืน', 'ค่าจัดส่งโดยประมาณ']]

    sale_ls = []
    for order_id in shopee_sale_df['หมายเลขคำสั่งซื้อ'].unique():
        df1 = shopee_sale_df[shopee_sale_df['หมายเลขคำสั่งซื้อ'] == order_id].reset_index(drop = True)
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

    return shopee_sale_df_result

@st.cache_data
def lazada_sale_df(file, store_name): 
    lazada_sale_df = pd.read_excel(file, converters={'orderNumber':str})

    
    lazada_sale_df = lazada_sale_df[~lazada_sale_df['status'].isin(['canceled', 'returned', 'Package Returned'])]
    lazada_sale_df['createTime'] = pd.to_datetime(lazada_sale_df['createTime'], format = '%d %b %Y %H:%M').dt.date

    lazada_sale_df = lazada_sale_df[['status', 'createTime', 'orderNumber', 'customerName', 'paidPrice', 'sellerDiscountTotal']]

    sale_ls = []
    for order_id in lazada_sale_df['orderNumber'].unique():
        df1 = lazada_sale_df[lazada_sale_df['orderNumber'] == order_id].reset_index(drop = True)

        order_date = df1.loc[0, 'createTime']
        order_no = str(df1.loc[0, 'orderNumber'])
        customer_name = df1.loc[0, 'customerName']
        # seller_discount_code = float(df1['sellerDiscountTotal'].sum())
        include_vat = df1['paidPrice'].sum()
        vat = round((include_vat * 0.07) / 1.07, 2)
        before_vat = include_vat - vat

        status = df1.loc[0, 'status']

        sale_ls.append(['Lazada', store_name, 'สินค้า', order_date, status, order_no, customer_name, before_vat, vat, include_vat])

    lazada_sale_df_result = pd.DataFrame(sale_ls, columns = ['platform', 'store_name', 'type', 'order_date', 'status', 'order_no', 'customer_name', 'before_vat', 'vat', 'include_vat'])
    lazada_sale_df_result = lazada_sale_df_result[['platform', 'store_name', 'type', 'order_date', 'status', 'order_no', 'customer_name', 'before_vat', 'vat', 'include_vat']]

    return lazada_sale_df_result          

@st.cache_data
def tiktok_sale_df(file, store_name):
    tiktok_sale_df = pd.read_csv(file, converters={'Order ID':str})

    tiktok_sale_df = tiktok_sale_df[~tiktok_sale_df['Order Status'].isin(['Canceled'])]
    tiktok_sale_df['Created Time'] = pd.to_datetime(tiktok_sale_df['Created Time'], format = '%d/%m/%Y %H:%M:%S ').dt.date

    tiktok_sale_df['SKU Subtotal Before Discount'] = tiktok_sale_df['SKU Subtotal Before Discount'].str.replace('THB ', '').str.replace(',', '').astype(float)
    tiktok_sale_df['SKU Seller Discount'] = tiktok_sale_df['SKU Seller Discount'].str.replace('THB ', '').str.replace(',', '').astype(float)
    tiktok_sale_df['Shipping Fee After Discount'] = tiktok_sale_df['Shipping Fee After Discount'].str.replace('THB ', '').str.replace(',', '').astype(float)
    tiktok_sale_df = tiktok_sale_df[['Order Status', 'Created Time', 'Order ID', 'Buyer Username', 'SKU Subtotal Before Discount', 'SKU Seller Discount',
                                    'Shipping Fee After Discount']]

    sale_ls = []
    for order_id in tiktok_sale_df['Order ID'].unique():
        df1 = tiktok_sale_df[tiktok_sale_df['Order ID'] == order_id].reset_index(drop = True)

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

    return tiktok_sale_df_result                 

####################################### sale #######################################
@st.cache_data
def shopee_commission(file):
    found_error = False
    shopee_pdf_d = {}
    ls = []
    with zipfile.ZipFile(file, 'r') as z: 
        sorted_file_ls = ['-'.join(ls) for ls in sorted([n.split('-') for n in z.namelist()], key = lambda x: int(x[4]))]
        shopee_bar = st.progress(len(sorted_file_ls), text = 'processing shopee commission pdf')
        for i, file_name in enumerate(sorted_file_ls[:5]):
            if 'SPX' in file_name:
                shopee_bar.progress((i + 1) / len(sorted_file_ls), text='reading shopee commission pdf files')
            else:
                pdf_file = pypdf.PdfReader(BytesIO(z.read(file_name)))

                doc_date, doc_num, issued_company, before_vat, vat, company_name, company_tax_id = None, None, None, None, None, None, None
                # st.write(pdf_file.pages[0].extract_text().split('\n'))
                for j, text in enumerate(pdf_file.pages[0].extract_text().split('\n')):
                    if 'วันที่' in text and 'ภายในวันที่' not in text:
                        doc_date = pd.to_datetime(text.split(' ')[-1], format = '%d/%m/%Y').date()
                    elif 'Co.,' in text:
                        issued_company = text
                    elif 'เลขที่' in text:
                        doc_num = text.split('No. ')[-1] + ' ' + pdf_file.pages[0].extract_text().split('\n')[j + 1]
                    elif 'after discount' in text:
                        before_vat = float(text.split(' ')[-1].replace(',', ''))
                    elif 'VAT' in text and '7%' in text:
                        vat = float(text.split(' ')[-1].replace(',', '')) 
                    elif 'Receipt/Tax Invoice' == text:
                        company_name = pdf_file.pages[0].extract_text().split('\n')[j + 1].split('Customer name ')[-1]
                        company_tax_id = pdf_file.pages[0].extract_text().split('\n')[j + 5].split('Tax ID ')[-1].split('เลขที่/')[0]
                
                st.write(doc_date)
                if None in [doc_date, company_name, company_tax_id, issued_company, doc_num, before_vat, vat]:
                    st.write(f'sth wrong with {file_name}')
                    found_error = True
                    break
                else:
                    ls.append([doc_date, company_name, company_tax_id, issued_company, doc_num, before_vat, vat])
                    shopee_pdf_d[len(shopee_pdf_d.keys())] = {'f': BytesIO(z.read(file_name)), 
                                                            'company_name': company_name, 
                                                            'date': doc_date}
                    shopee_bar.progress((i + 1) / len(sorted_file_ls), text='reading shopee commission pdf file')
                    # break ##

    shopee_commission_df = pd.DataFrame(ls, columns = ['doc_date', 'company_name', 'company_tax_id', 'issued_company', 'doc_num', 'before_vat', 'vat'])
    shopee_commission_df = shopee_commission_df.sort_values(by = ['doc_date', 'doc_num'], ascending = [True, True]).reset_index(drop = True)
    shopee_bar.empty()

    # st.write(shopee_df_d)
    return [shopee_commission_df if not found_error else f'sth wrong with {file_name}', shopee_pdf_d]

@st.cache_resource #note file date list
def lazada_commission(file_ls, selected_month_name):
    ls = []
    doc_num_ls = [] #กรณี upload file ซ้ำ
    file_date_ls = []

    lazada_bar = st.progress(len(file_ls), text = 'processing lazada commission pdf')
    for file_order, file_name in enumerate(file_ls):
        pdf_file = pypdf.PdfReader(file_name)

        if 'Lazada Express Limited' in pdf_file.pages[0].extract_text() or 'Shipping Fee' in pdf_file.pages[0].extract_text():
            lazada_bar.progress((file_order + 1) / len(file_ls), text='reading shopee commission pdf files')
        else:
            # st.write('file_name = ', file_name.name)
            # st.write(pdf_file.pages[0].extract_text().split('\n'))
            
            doc_date, doc_num, issued_company, before_vat, vat, company_name, company_tax_id = None, None, None, None, None, None, None
            # st.write(pdf_file.pages[0].extract_text().split('\n'))
            for i, text in enumerate(pdf_file.pages[0].extract_text().split('\n')):
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

            
            if doc_num in doc_num_ls: #ไฟล์ที่อ่าน มีเลขเอกสารซ้ำ น่าจะเพราะอัพโหลดมาซ้ำ
                lazada_bar.progress((file_order + 1) / len(file_ls), text='reading Lazada commission pdf files')
            else:
                if None in [doc_date, company_name, company_tax_id, issued_company, doc_num, before_vat, vat, company_name, company_tax_id]:
                    st.write('sth wrong')
                    break
                else:
                    doc_num_ls.append(doc_num)
                    file_date_ls.append([doc_date, pdf_file, company_name])
                    ls.append([doc_date, company_name, company_tax_id, issued_company, doc_num, before_vat, vat])

                    lazada_bar.progress((file_order + 1) / len(file_ls), text='reading Lazada commission pdf files')
            
                    
    lazada_pdf_d = {} #index = 0, 1, 2 ....
    for ls2 in sorted(file_date_ls, key=lambda x: x[0]): #sort by doc date
        st.write(ls2)
        st.write(ls2[0].strftime('%b'))
        st.write(selected_month_name)
        if doc_date.strftime('%b') == month_option:
            lazada_pdf_d[len(list(lazada_pdf_d.keys()))] = {'f': ls2[-2], 
                                                        'company_name': ls2[-1], 
                                                        'date': ls2[0]}
            st.write(lazada_pdf_d)
        # file_order[-1].seek(0)
        # merger.append(file_order[-1])

    st.write(lazada_pdf_d)

    lazada_commission_df = pd.DataFrame(ls, columns = ['doc_date', 'company_name', 'company_tax_id', 'issued_company', 'doc_num', 'before_vat', 'vat'])
    lazada_commission_df = lazada_commission_df.sort_values(by = ['doc_date', 'doc_num'], ascending = [True, True]).reset_index(drop = True)
    lazada_bar.empty()

    return [lazada_commission_df, lazada_pdf_d]
    # st.dataframe(lazada_commission_df)

@st.cache_data
def tiktok_commission(file):
    ls = []
    with zipfile.ZipFile(file,'r') as z:
        sorted_file_ls = sorted([n for n in z.namelist()])
        tiktok_bar = st.progress(len(sorted_file_ls), text = 'processing tiktok commission pdf')
        for i, file_name in enumerate(sorted_file_ls):
            if 'THJV' in file_name or 'TTSTHAC' in file_name:
                tiktok_bar.progress((i + 1) / len(sorted_file_ls), text='reading tiktok commission pdf files')
            else:
                pdf_file = pypdf.PdfReader(BytesIO(z.read(file_name)))
                # break
                doc_date, doc_num, company, before_vat, vat, company_name, company_tax_id = None, None, None, None, None, None, None
                # st.write(pdf_file.pages[0].extract_text().split('\n'))
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
                    st.write(f'sth wrong with {file_name}')
                    st.write([doc_date, company_name, company_tax_id, issued_company, doc_num, before_vat, vat])
                    break
                else:
                    ls.append([doc_date, company_name, company_tax_id, issued_company, doc_num, before_vat, vat])
                    merger.append(BytesIO(z.read(file_name)))
                    tiktok_bar.progress((i + 1) / len(sorted_file_ls), text='reading tiktok commission pdf file')
                    # st.write(merger)
                    # break ##

    tiktok_commission_df = pd.DataFrame(ls, columns = ['doc_date', 'company_name', 'company_tax_id', 'issued_company', 'doc_num', 'before_vat', 'vat'])
    tiktok_commission_df = tiktok_commission_df.sort_values(by = ['doc_date', 'doc_num'], ascending = [True, True]).reset_index(drop = True)
    tiktok_bar.empty()

    return tiktok_commission_df

#%%กรณี upload file ผิด เช่น upload pdf ของ shpoee
st.header('VAT app')

with st.sidebar:
    sidebar_radio = st.radio(
        "sidebar menu",
        ("check if 1.8M", 
        "vat cal", 
        'button'), 
        index = 1
    )

if sidebar_radio == 'check if 1.8M':
    pass

elif sidebar_radio == 'vat cal':
    st.write('มาเพิ่ม ถ้าคำสั่งซื้อยังไม่สำเร็จ')
    cont = True

    store_number = st.number_input(
        label = 'how many store you have', 
        min_value = 1, 
        max_value = 5, 
        value = 1, 
        step = 1
    )

    month_option = st.selectbox(
        label = 'select month', 
        options = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], 
        index = (pd.to_datetime('now').replace(day = 1) - pd.Timedelta(days = 1)).month - 1
    )

    store_name = st.text_input(
        label = 'type in your store name', 
        value = None
    )


    if store_name is not None:
        #note: ถ้าไฟล์ที่อัพโหลดมามียอดขายของหลายเดือน?
        st.divider()
        st.subheader('1. select platform you have your store on (press enter after fill in)')
        in_shopee = st.checkbox('in_shopee')
        in_lazada = st.checkbox('in_lazada')
        in_tiktok = st.checkbox('in_tiktok')

        if True in [in_shopee, in_lazada, in_tiktok]:
            
            st.divider()
            st.subheader('2. part upload ไฟล์ยอดขาย')

            #upload sale file
            if in_shopee:
                # st.write("##")
                st.markdown("<h4>Shopee</h4>", unsafe_allow_html=True)
                shopee_sale_file = st.file_uploader(
                    label = 'upload file ยอดขายของ shopee (.xlsx)', 
                    accept_multiple_files = False,
                    type = 'xlsx'
                )
            
            if in_lazada:
                # st.write("##")
                st.markdown("<h4>Lazada</h4>", unsafe_allow_html=True)
                lazada_sale_file = st.file_uploader(
                    label = 'upload file ยอดขายของ lazada (.xlsx)', 
                    accept_multiple_files = False, 
                    type = 'xlsx'
                )
            
            if in_tiktok:
                # st.write("##")
                st.markdown("<h4>TikTok</h4>", unsafe_allow_html=True)
                tiktok_sale_file = st.file_uploader(
                    label = 'upload file ยอดขายของ tiktok (.csv)', 
                    accept_multiple_files = False, 
                    type = 'csv'
                )

            st.divider()
            st.subheader('3. part upload ไฟล์ใบเสร็จ commission')

            #upload commission files
            # st.write("##")
            if in_shopee:
                st.markdown("<h4>Shopee</h4>", unsafe_allow_html=True)
                shopee_commission_file = st.file_uploader(
                    label = 'upload file ใบเสร็จค่าธรรมเนียม shopee (.zip)', 
                    accept_multiple_files = False,
                    type = 'zip'
                )

            # st.write("#")
            if in_lazada:
                st.markdown("<h4>Lazada</h4>", unsafe_allow_html=True)
                lazada_commission_files = st.file_uploader(
                    label = 'upload file ใบเสร็จค่าธรรมเนียม lazada (.pdf) ลากมาหลายๆไฟล์ทีเดียวได้เลย', 
                    accept_multiple_files = True, 
                    type = 'pdf'
                    )
            
            # st.write('##')
            if in_tiktok:
                st.markdown("<h4>TikTok</h4>", unsafe_allow_html=True)
                tiktoK_commission_file = st.file_uploader(
                    label = 'upload file ใบเสร็จค่าธรรมเนียม tiktok (.zip)', 
                    accept_multiple_files = False, 
                    type = 'zip'
                    )

            st.divider()
            col1, col2, col3 = st.columns([2, 1, 2])

            if 'vat_cal_clicked' not in st.session_state:
                st.session_state.vat_cal_clicked = False

            def click_button():
                st.session_state.vat_cal_clicked = True

            col2.button('calculate', on_click = click_button, use_container_width = True)

            if st.session_state.vat_cal_clicked:
                #for commission pdf merging
                # merger = PdfMerger()

                if in_shopee:
                    if shopee_sale_file is not None and shopee_commission_file is not None:
                        #sale
                        shopee_info = st.info('calculating sale from Shopee!', icon="ℹ️")

                        shopee_sale_df_result = shopee_sale_df(file = shopee_sale_file, store_name = store_name)
                        shopee_info.empty()
                        shopee_info.info('calculating commission from Shopee!', icon="ℹ️")
                        
                        shopee_commission_df = shopee_commission(file = shopee_commission_file)[0]
                        shopee_pdf_d = shopee_commission(file = shopee_commission_file)[1]
                        st.write('shopee_pdf_d -->', shopee_commission(file = shopee_commission_file)[1])
                        
                        shopee_info.success('finish shopee!!!')

                    else:
                        if shopee_sale_file is None:
                            st.write('please upload shopee sale file')
                        elif shopee_commission_file is None:
                            st.write('please upload shopee commission file')
                        
                        cont = False

                if in_lazada and cont:
                    if lazada_sale_file is not None and lazada_commission_files != []:
                        lazada_info = st.info('calculating sale from Lazada!', icon="ℹ️")

                        lazada_sale_df_result = lazada_sale_df(file = lazada_sale_file, store_name = store_name)

                        # lazada_info.empty()
                        lazada_info.info('calculating commission from Lazada!', icon="ℹ️")
                        st.write('aaa')
                        lazada_commission_df = lazada_commission(file_ls = lazada_commission_files, selected_month_name=month_option)[0]
                        
                        lazada_pdf_d = lazada_commission(file_ls = lazada_commission_files, selected_month_name=month_option)[1]

                        st.write(lazada_pdf_d)
                        
                        # lazada_bar.empty()
                        lazada_info.success('finish lazada!!!')

                    else:
                        if lazada_sale_file is None:
                            st.write('please upload lazada sale file')
                        elif lazada_commission_files == []:
                            st.write('please upload lazada commission files')
                        
                        cont = False


                if in_tiktok and cont:
                    if tiktok_sale_file is not None:
                        tiktok_info = st.info('calculating sale from TikTok!', icon="ℹ️")

                        tiktok_sale_df_result = tiktok_sale_df(tiktok_sale_file, store_name = store_name)
                        
                        tiktok_info.empty()
                        tiktok_info.info('calculating commission from TikTok!', icon="ℹ️")

                        
                        tiktok_commission_df = tiktok_commission(tiktoK_commission_file)

                        # tiktok_bar.empty()
                        tiktok_info.success('finish TikTok!!!')

                    else:
                        if tiktok_sale_file is None:
                            st.write('please upload TikTok sale file')
                        elif tiktoK_commission_file is None:
                            st.write('please upload TikTok commission files')
                        
                        cont = False

                if cont:
                    sale_df = pd.concat(
                        [
                            shopee_sale_df_result if 'shopee_sale_df_result' in locals() else pd.DataFrame(), 
                            lazada_sale_df_result if 'lazada_sale_df_result' in locals() else pd.DataFrame(), 
                            tiktok_sale_df_result if 'tiktok_sale_df_result' in locals() else pd.DataFrame()
                        ], 
                        axis = 0
                    ).reset_index(drop = True)

                    st.dataframe(sale_df)

                    commission_df = pd.concat(
                        [
                            shopee_commission_df if 'shopee_commission_df' in locals() else pd.DataFrame(), 
                            lazada_commission_df if 'lazada_commission_df' in locals() else pd.DataFrame(), 
                            tiktok_commission_df if 'tiktok_commission_df' in locals() else pd.DataFrame()
                        ], 
                        axis = 0
                    ).reset_index(drop = True)

                    # st.dataframe(sale_df)
                    
                    # commission_df = pd.concat([pd.DataFrame({'check': [False] * commission_df.shape[0]}), commission_df], axis = 1)

                    st.divider()
                    st.write(len(commission_df['company_tax_id'].str.lower().str.replace(' ', '').unique()))
                    
                    if len(commission_df['company_tax_id'].str.lower().str.replace(' ', '').unique()) >= 2:
                        st.subheader('5. check')
                        st.warning('เจอชื่อ บ ในใบเสร็จ มากกว่า 1 ชื่อ --> กรุณาเลือกชื่อผู้จ่าย vat ที่ถูกต้อง', icon="⚠️")

                        if not 'company_tax_id' in st.session_state:
                            st.session_state.company_tax_id = []
        
                        # commission_df['company_name1'] = commission_df['company_name'].str.lower().str.replace(' ', '')
                        for i, tax_id in enumerate(commission_df['company_tax_id'].str.replace(' ', '').unique().tolist()):
                            # in_shopee = st.checkbox('in_shopee')
                            if tax_id not in st.session_state.company_tax_id:
                                st.session_state.company_tax_id.append(tax_id)
                            
                            # show_name = commission_df[commission_df['company_name1'] == name]['company_name'].tolist()[0]
                            name = commission_df[commission_df['company_tax_id'].str.replace(' ', '') == tax_id].reset_index(drop = True).loc[0, 'company_name']
                            st.checkbox(label=f'{name}', key=tax_id)
                            st.dataframe(commission_df[commission_df['company_tax_id'] == tax_id])
                        
                        st.write(st.session_state)
                        commission_df1 = pd.DataFrame()
                        for tax_id in st.session_state.company_tax_id:
                            # st.write(tax_id)
                            if st.session_state[tax_id.replace(' ', '').lower()]:
                                commission_df1 = pd.concat([commission_df1, commission_df[commission_df['company_tax_id'] == tax_id]], axis = 0).reset_index(drop = True)

                    

                        st.write(st.session_state)
                        st.dataframe(commission_df1)

                        if st.button('finish ticking'):
                            ready_to_download = True
                        else:
                            ready_to_download = False


                    else:
                        ready_to_download = True

                    st.divider()


                    if ready_to_download:

                        merger = PdfMerger()
                        st.dataframe(commission_df1)
                        st.write(shopee_pdf_d)
                        for key, value in shopee_pdf_d.items():
                            if value['company_name'] in commission_df1['company_name'].tolist():
                                st.write('aaa')
                                # value['f'].seek(0)
                                st.write('bbb')
                                merger.append(value['f'])

                        st.write(lazada_pdf_d)

                        merged_pdf = BytesIO()
                        merger.write(merged_pdf)
                        merger.close()

                        merged_pdf.seek(0)

                        buffer = BytesIO()
                        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
                            
                            for i, df in enumerate([sale_df, commission_df1]):
                                excel_buffer = BytesIO()
                                with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                                    df.to_excel(writer, index=False, sheet_name="Sheet1")
                                excel_buffer.seek(0)

                                zipf.writestr('sale_df.xlsx' if i == 0 else 'commission_df.xlsx', excel_buffer.getvalue())

                            zipf.writestr("merged.pdf", merged_pdf.read())

                        buffer.seek(0)

                        st.download_button(
                            label = "download final file",
                            data = buffer,
                            file_name = "aaa.zip",
                            mime = "application/zip"
                    )
                    
                        

                        
