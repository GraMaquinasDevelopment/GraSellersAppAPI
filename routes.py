import datetime
import json
import logging
import os
import traceback
import uuid
from difflib import get_close_matches
from typing import List, Dict
from venv import logger

import aiofiles
import jwt
from fastapi import APIRouter, HTTPException, Depends, Body, Header, UploadFile, File, Query
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette import status

import database  # Certifique-se de que o módulo database está implementado corretamente
from companyEquipmentsExcelFile import process_excel_data

router = APIRouter()
security = HTTPBearer()


# Obtém a SECRET_KEY da variável de ambiente
SECRET_KEY = "1e255487c1c756ce12133c0762a16fe5779ca1d313470369436f32c2190f56d08eeb0aced2217aeba658a246ac773d01392478e341e56ee1c68a343270d38dfd"
ALGORITHM = "HS256"

async def validate_token(credentials: HTTPAuthorizationCredentials):
    token = credentials.credentials

    # Se o token for o especial, pula toda a validação e retorna algo simples
    if token == "Al9sjS1w-8FAXC6vIf584zomaXl61Hj73jHlTFImfBA":
        print("Token especial detectado, pulando validação completa.")
        return {"special_token": True}

    try:
        # Decodifica o token e valida a assinatura
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Log do payload decodificado
        print(f"Payload decodificado: {payload}")

        # Extrai os dados do payload
        user_id = payload.get("id")
        email = payload.get("email")
        document = payload.get("document")
        password_version = payload.get("passwordVersion")

        # Verifica se todos os dados necessários estão presentes
        if not all([user_id, email, document, password_version]):
            raise HTTPException(status_code=400, detail="Dados insuficientes no token")

        # Conecta ao banco de dados e obtém um cursor
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Consulta o banco de dados para validar o usuário
        query = """
        SELECT * 
        FROM users
        WHERE id = %s AND email = %s AND document = %s AND passwordVersion = %s AND isActive = 1
        """
        cursor.execute(query, (user_id, email, document, password_version))
        user_data = cursor.fetchone()
        cursor.close()
        connection.close()

        # Se não encontrar nenhum registro, lança uma exceção
        if user_data is None:
            raise HTTPException(status_code=401, detail="Token inválido ou expirado")

        return payload

    except jwt.PyJWTError as e:
        # Log do erro se o token não for válido
        print(f"Erro ao decodificar o token: {str(e)}")
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")


def format_json(data: dict) -> str:
    return json.dumps(data, indent=4, sort_keys=True)


@router.post("/post/customers")
async def get_customers(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request_data: List[Dict] = Body(...),
    expected_inserts: int = Body(...)
):
    print('Ta entrando aqui 12')
    # Valida o token
    await validate_token(credentials)

    # Processa o JSON recebido
    received_data = request_data

    # Conecta ao banco de dados
    connection = database.connect_to_database()
    cursor = connection.cursor()

    # Desativa o modo autocommit para iniciar a transação
    connection.autocommit = False
    logger.info(f"expected_inserts: {expected_inserts}")


    try:
        total_inserts = 0
        print('Ta entrando aqui 12222')
        for customer in received_data:

            # Tabela address
            address_uid = customer.get("addressUID")
            description = customer.get("addressdescription")
            description = None if description == '' else description
            neighborhood = customer.get("neighborhood")
            number = customer.get("number")
            complement = customer.get("complement")
            addresscreatedate = customer.get("addresscreatedate")
            addresscreateuserid = customer.get("addresscreateuserid")
            addressisactive = customer.get("addressisactive")
            city_uid = customer.get("cityUID")
            print('Ta entrando aqui 14444442')
            # Verifica se todos os campos obrigatórios estão presentes
            if not all([address_uid, addresscreatedate, addresscreateuserid, addressisactive, city_uid]):
                raise HTTPException(status_code=400, detail="Dados insuficientes para inserção")

            # Verifica se addressUID já existe
            cursor.execute("SELECT COUNT(*) FROM address WHERE addressUID = %s", (address_uid,))
            address_exists = cursor.fetchone()[0] > 0
            print('Ta entrando aqui 1344322423')
            print(description)
            if address_exists:
                # Faz o UPDATE na tabela address
                query = """
                    UPDATE address
                    SET description = %s, neighborhood = %s, number = %s, complement = %s, createdate = NOW(), createuserid = %s, isActive = %s, cityUID = %s
                    WHERE addressUID = %s
                """
                cursor.execute(query, (
                description, neighborhood, number, complement, addresscreateuserid, addressisactive, city_uid,
                address_uid))

            else:
                print('ta entrando aqqqqqq')
                # Faz o INSERT na tabela address
                query = """
                          INSERT INTO address (addressUID, description, neighborhood, number, complement, createdate, createuserid, isActive, cityUID)
                          VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """
                cursor.execute(query, (address_uid, description, neighborhood, number, complement, addresscreatedate, addresscreateuserid, addressisactive, city_uid))

            total_inserts += 1

            # Tabela contact
            contact_uids = (customer.get("contactUID") or "").split(",")
            print('Ta entrando aqui 1777777777777')
            responsibles = (customer.get("responsible") or "").split(",")
            phones = (customer.get("phone") or "").split(",")
            emails = (customer.get("email") or "").split(",")
            contactcreatedate = customer.get("contactcreatedate", "")
            contactcreateuserids = (customer.get("contactcreateuserid") or "").split(",")
            contactisactives = (customer.get("contactisactive") or "").split(",")

            # Contar o número de contatos
            num_contacts = len(contact_uids)

            print("Tamanhos recebidos:")
            print("responsibles:", len(responsibles))
            print("phones:", len(phones))
            print("emails:", len(emails))
            print("contactcreateuserids:", len(contactcreateuserids))
            print("contactisactives:", len(contactisactives))
            print("num_contacts:", num_contacts)

            # Verificar se todos os campos têm o mesmo número de registros
            #if not (len(responsibles) == len(phones) == len(emails) == len(contactcreateuserids) == len(contactisactives) == num_contacts):
                #raise HTTPException(status_code=400, detail="Dados de contato inconsistentes")

            customer_uid = customer.get("customerUID")
            # Obtém todos os contactUIDs relacionados ao customerUID fornecido
            cursor.execute("SELECT contactUID FROM customer_has_contact WHERE customerUID = %s", (customer_uid,))
            contact_uids_to_delete = [row[0] for row in cursor.fetchall()]

            # Limpa a tabela customer_has_contact para o customerUID fornecido
            cursor.execute("DELETE FROM customer_has_contact WHERE customerUID = %s", (customer_uid,))

            # Limpa a tabela contact usando os contactUIDs obtidos
            if contact_uids_to_delete:
                # Constrói a consulta de exclusão dinâmica
                delete_query = "DELETE FROM contact WHERE contactUID IN (%s)" % ','.join(
                    ['%s'] * len(contact_uids_to_delete))
                cursor.execute(delete_query, tuple(contact_uids_to_delete))

            print('Ta entrando aqui 100000000000000000')
            for i in range(num_contacts):

                # Obter os valores individuais e remover espaços em branco
                contact_uid = contact_uids[i].strip()

                responsible = responsibles[i].strip()
                phone = phones[i].strip()
                email = emails[i].strip()

                # Verifica se o email é '0' e substitui por None
                email = None if email == '0' else email


                # Verifica se createuserid e isactive são válidos
                createuserid = int(contactcreateuserids[i].strip()) if contactcreateuserids[i].strip() else None
                isactive = int(contactisactives[i].strip()) if contactisactives[i].strip() else None

                # Pega o primeiro valor de contactcreatedate, assumindo que pode haver múltiplos valores separados por vírgula
                contact_createdate_list = contactcreatedate.split(",")
                contact_createdate = contact_createdate_list[i].strip() if i < len(contact_createdate_list) else None

                # Inserir no banco de dados
                query_contact = """
                    INSERT INTO contact (contactUID, responsible, phone, email, createdate, createuserid, isActive)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                values_contact = (contact_uid, responsible, phone, email, contact_createdate, createuserid, isactive)
                cursor.execute(query_contact, values_contact)

                total_inserts += 1

            # Tabela equipment
            equipment_uid = customer.get("equipmentUID")
            equipment_description = customer.get("equipmentdescription")
            equipment_createdate = customer.get("equipmentcreatedate")
            equipment_createuserid = customer.get("equipmentcreateuserid")
            equipment_isactive = customer.get("equipmentisactive")

            print('Ta entrando aqui 1456456456456456')
                    # Verifica se equipmentUID é None ou string vazia e pula o insert se for o caso
            if equipment_uid:
                # Remove espaços em branco e converte os valores conforme necessário
                equipment_uid = equipment_uid.strip() if isinstance(equipment_uid, str) else equipment_uid
                equipment_description = equipment_description.strip() if isinstance(equipment_description, str) else equipment_description
                equipment_createdate = equipment_createdate.strip() if isinstance(equipment_createdate, str) else equipment_createdate
                equipment_createuserid = int(equipment_createuserid) if equipment_createuserid and isinstance(equipment_createuserid, str) and equipment_createuserid.isdigit() else equipment_createuserid
                equipment_isactive = int(equipment_isactive) if equipment_isactive and isinstance(equipment_isactive, str) and equipment_isactive.isdigit() else equipment_isactive

                # Verifica se equipmentUID já existe
                cursor.execute("SELECT COUNT(*) FROM equipment WHERE equipmentUID = %s", (equipment_uid,))
                equipment_exists = cursor.fetchone()[0] > 0

                print('Ta entrando aqui 234233242342344324')
                if equipment_exists:
                    # Faz o UPDATE na tabela equipment
                    query_equipment = """
                        UPDATE equipment
                        SET description = %s, createdate = %s, createuserid = %s, isActive = %s
                        WHERE equipmentUID = %s
                    """
                    values_equipment = (equipment_description, equipment_createdate, equipment_createuserid, equipment_isactive, equipment_uid)
                    cursor.execute(query_equipment, values_equipment)

                else:

                    # Inserir no banco de dados
                    query_equipment = """
                        INSERT INTO equipment (equipmentUID, description, createdate, createuserid, isActive)
                        VALUES (%s, %s, %s, %s, %s)
                    """
                    values_equipment = (equipment_uid, equipment_description, equipment_createdate, equipment_createuserid, equipment_isactive)
                    cursor.execute(query_equipment, values_equipment)
                total_inserts += 1
        print('Ta entrando aqui 33234')
        # Loop para inserir ou atualizar todos os registros de customer depois dos outros registros
        for customer in received_data:
            # Obtém os valores de customer
            customer_uid = customer.get("customerUID")
            name = customer.get("name")
            document = customer.get("document")
            address_uid = customer.get("addressUID")
            customertype_uid = customer.get("customertypeUID")
            equipment_uid = customer.get("equipmentUID")  # Campo opcional, pode ser None
            customer_createdate = customer.get("customercreatedate")
            customer_createuserid = customer.get("customercreateuserid")
            customer_isactive = customer.get("customerisactive")

            print('Ta entrando aqui 0')
            # Verifica se todos os campos obrigatórios estão presentes
            if all([customer_uid, name, address_uid, customertype_uid, customer_createdate, customer_createuserid, customer_isactive]):
                # Remove espaços em branco e converte os valores conforme necessário
                print('Ta entrando aqui 1')
                customer_uid = customer_uid.strip()
                name = name.strip()
                document = document.strip() if document else None
                address_uid = address_uid.strip()
                customertype_uid = customertype_uid.strip()
                equipment_uid = equipment_uid.strip() if equipment_uid else None  # Campo opcional
                customer_createdate = customer_createdate.strip()
                customer_createuserid = int(customer_createuserid) if isinstance(customer_createuserid, str) and customer_createuserid.isdigit() else customer_createuserid
                customer_isactive = int(customer_isactive) if isinstance(customer_isactive, str) and customer_isactive.isdigit() else customer_isactive
                print('Ta entrando aqui 2')
                # Verifica se customerUID já existe
                cursor.execute("SELECT COUNT(*) FROM customer WHERE customerUID = %s", (customer_uid,))
                customer_exists = cursor.fetchone()[0] > 0
                print('Ta entrando aqui 3')
                print(name)
                if customer_exists:
                    # Faz o UPDATE na tabela customer
                    query_customer = """
                        UPDATE customer
                        SET name = %s, document = %s, addressUID = %s, customertypeUID = %s, equipmentUID = %s, createdate = NOW(), createuserid = %s, isActive = %s
                        WHERE customerUID = %s
                    """
                    values_customer = (
                    name, document, address_uid, customertype_uid, equipment_uid, customer_createuserid,
                    customer_isactive, customer_uid)
                    cursor.execute(query_customer, values_customer)
                else:
                    print('Ta entrando aqui 4')
                    # Inserir no banco de dados
                    query_customer = """
                        INSERT INTO customer (customerUID, name, document, addressUID, customertypeUID, equipmentUID, createdate, createuserid, isActive)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    values_customer = (customer_uid, name, document, address_uid, customertype_uid, equipment_uid, customer_createdate, customer_createuserid, customer_isactive)
                    cursor.execute(query_customer, values_customer)
                total_inserts += 1

        # Inserção ou atualização na tabela 'customer_has_contact'
        for customer in received_data:
            customer_uid = customer.get("customerUID")
            contact_uids = (customer.get("contactUID") or "").split(",")

            for contact_uid in contact_uids:
                contact_uid = contact_uid.strip()
                if contact_uid:  # Verifica se o contactUID não é vazio
                    # Verifica se a combinação customerUID e contactUID já existe
                    cursor.execute("SELECT COUNT(*) FROM customer_has_contact WHERE customerUID = %s AND contactUID = %s", (customer_uid, contact_uid))
                    customer_contact_exists = cursor.fetchone()[0] > 0

                    if not customer_contact_exists:
                        query_customer_has_contact = """
                            INSERT INTO customer_has_contact (customerUID, contactUID)
                            VALUES (%s, %s)
                        """
                        values_customer_has_contact = (customer_uid, contact_uid)
                        cursor.execute(query_customer_has_contact, values_customer_has_contact)
                        total_inserts += 1

        # Confirma as alterações no banco de dados se o número de inserts for maior ou igual ao número de registros recebidos
        if total_inserts >= expected_inserts * 4:
            logger.info(f"total_inserts customers: {total_inserts}")
            logger.info(f"expected_inserts customers: {expected_inserts}")
            connection.commit()
            response_message = "Todos os registros foram inseridos/atualizados com sucesso."
        else:
            connection.rollback()
            response_message = "Erro ao inserir/atualizar dados no banco de dados. Operação revertida."

    except Exception as e:
        # Reverte a transação em caso de erro
        connection.rollback()
        logger.error(f"Erro durante a inserção/atualização: {e}")
        response_message = f"Erro durante a inserção/atualização: {str(e)}"

    finally:
        # Fecha a conexão
        cursor.close()
        connection.close()

    return JSONResponse(content={"message": response_message}, status_code=200 if total_inserts >= expected_inserts else 400)

@router.post("/post/negotiations_and_visits")
async def post_negotiations_and_visits(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request_data: List[Dict] = Body(...),
    expected_negotiations: int = Body(...),
    expected_visits: int = Body(...)
):
    # Valida o token
    payload = await validate_token(credentials)

    # Processa o JSON recebido
    received_data = request_data

    # Conecta ao banco de dados
    connection = database.connect_to_database()
    cursor = connection.cursor()

    try:
        # Contadores de negociações e visitas inseridas/atualizadas
        inserted_negotiations = 0
        inserted_visits = 0

        # Inserção/Atualização de negociações
        for negotiation in received_data:
            negotiation_uid = negotiation.get("negotiationUID")
            customer_uid = negotiation.get("customerUID")
            closingforecast_uid = negotiation.get("closingforecastUID")
            negotiationstatus_uid = negotiation.get("negotiationstatusUID")
            customersource_uid = negotiation.get("customersourceUID")
            priority_uid = negotiation.get("priorityUID")
            note = negotiation.get("note")
            negotiationdate = negotiation.get("negotiationdate")
            negotiation_createdate = negotiation.get("negotiationcreatedate")
            negotiation_createuserid = negotiation.get("negotiationcreateuserid")
            negotiation_isactive = negotiation.get("negotiationisactive")
            negotiation_issynchronized = negotiation.get("negotiationissynchronized")

            # Verifica se todos os campos obrigatórios estão presentes
            if not all([negotiation_uid, customer_uid, closingforecast_uid,negotiationdate, negotiationstatus_uid, customersource_uid,
                        priority_uid, negotiation_createdate, negotiation_createuserid, negotiation_isactive, negotiation_issynchronized is not None]):
                raise HTTPException(status_code=400, detail="Dados insuficientes para inserção de negociação")

            # Remove espaços em branco e converte os valores conforme necessário
            negotiation_uid = negotiation_uid.strip()
            customer_uid = customer_uid.strip()
            closingforecast_uid = closingforecast_uid.strip()
            negotiationstatus_uid = negotiationstatus_uid.strip()
            customersource_uid = customersource_uid.strip()
            priority_uid = priority_uid.strip()
            note = note.strip() if note else None
            negotiationdate = negotiationdate.strip()
            negotiation_createdate = negotiation_createdate.strip()
            negotiation_createuserid = int(negotiation_createuserid) if isinstance(negotiation_createuserid, str) and negotiation_createuserid.isdigit() else negotiation_createuserid
            negotiation_isactive = int(negotiation_isactive) if isinstance(negotiation_isactive, str) and negotiation_isactive.isdigit() else negotiation_isactive
            negotiation_issynchronized = int(negotiation_issynchronized) if isinstance(negotiation_issynchronized, str) and negotiation_issynchronized.isdigit() else negotiation_issynchronized

            if negotiation_issynchronized == 0:
                # Verificar se o negotiationUID já existe no banco de dados
                query_check_negotiation = "SELECT COUNT(*) FROM negotiation WHERE negotiationUID = %s"
                cursor.execute(query_check_negotiation, (negotiation_uid,))
                exists_negotiation = cursor.fetchone()[0]

                if exists_negotiation:
                    # Atualizar negociação existente
                    query_update_negotiation = """
                                               UPDATE negotiation
                                               SET customerUID          = %s, \
                                                   closingforecastUID   = %s, \
                                                   negotiationstatusUID = %s, \
                                                   customersourceUID    = %s,
                                                   priorityUID          = %s, \
                                                   note                 = %s, \
                                                   createdate           = NOW(), \
                                                   createuserid         = %s, \
                                                   isActive             = %s
                                               WHERE negotiationUID = %s \
                                               """
                    values_update_negotiation = (
                        customer_uid, closingforecast_uid, negotiationstatus_uid,
                        customersource_uid, priority_uid, note,
                        negotiation_createuserid, negotiation_isactive, negotiation_uid
                    )

                    # 👇 Adicione este print para ver os valores
                    print("Valores da query de UPDATE negotiation:")
                    for i, val in enumerate(values_update_negotiation):
                        print(f"  Param {i + 1}: {val}")

                    cursor.execute(query_update_negotiation, values_update_negotiation)

                else:
                    logging.basicConfig(level=logging.INFO)
                    # Inserir nova negociação
                    # Definindo a consulta de inserção e os valores
                    query_insert_negotiation = """
                        INSERT INTO negotiation (negotiationUID, customerUID, closingforecastUID, negotiationstatusUID, customersourceUID, priorityUID, note, createdate, createuserid, isActive,negotiationdate)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
                    """
                    values_insert_negotiation = (
                        negotiation_uid, customer_uid, closingforecast_uid, negotiationstatus_uid,
                        customersource_uid, priority_uid, note, negotiation_createdate,
                        negotiation_createuserid, negotiation_isactive, negotiationdate
                    )

                    # Imprimindo os valores no log
                    logging.info("Executando INSERT na tabela negotiation com os seguintes valores:")
                    logging.info("negotiationUID: %s", negotiation_uid)
                    logging.info("customerUID: %s", customer_uid)
                    logging.info("closingforecastUID: %s", closingforecast_uid)
                    logging.info("negotiationstatusUID: %s", negotiationstatus_uid)
                    logging.info("customersourceUID: %s", customersource_uid)
                    logging.info("priorityUID: %s", priority_uid)
                    logging.info("note: %s", note)
                    logging.info("createdate: %s", negotiation_createdate)
                    logging.info("createuserid: %s", negotiation_createuserid)
                    logging.info("isActive: %s", negotiation_isactive)

                    # Executando o comando de inserção
                    cursor.execute(query_insert_negotiation, values_insert_negotiation)

                    # Capturando o retorno do banco
                    rows_affected_negotiation = cursor.rowcount  # Número de linhas afetadas pelo INSERT

                    # Registrando o resultado no log
                    logging.info("INSERT executado com sucesso na tabela negotiation. Linhas afetadas: %d",
                                 rows_affected_negotiation)

                inserted_negotiations += 1

                # Manipulação de companyequipment_has_negotiation
                company_equipment_uids = negotiation.get("companyequipmentUID", "")
                company_equipment_values = negotiation.get("companyequipmentvalue", "")
                company_equipment_quantities = negotiation.get("companyequipmentquantity", "")

                if isinstance(company_equipment_uids, str) and isinstance(company_equipment_values, str):
                    company_equipment_uids = company_equipment_uids.split(",")
                    company_equipment_values = company_equipment_values.split(",")
                    company_equipment_quantities = company_equipment_quantities.split(",")

                    # Deletar registros existentes
                    query_delete_companyequipment = """
                        DELETE FROM companyequipment_has_negotiation WHERE negotiationUID = %s
                    """
                    cursor.execute(query_delete_companyequipment, (negotiation_uid,))

                    for equipment_uid, value, quantity in zip(company_equipment_uids, company_equipment_values, company_equipment_quantities):
                        equipment_uid = equipment_uid.strip()
                        value = value.strip() if value.strip() else "0"
                        quantity = quantity.strip() if quantity.strip() else "0"

                        if equipment_uid:
                            query_insert_companyequipment = """
                                INSERT INTO companyequipment_has_negotiation (negotiationUID, companyequipmentUID, value, quantity)
                                VALUES (%s, %s, %s, %s)
                            """
                            values_companyequipment = (negotiation_uid, equipment_uid, value, quantity)
                            cursor.execute(query_insert_companyequipment, values_companyequipment)

            # Inserção/Atualização de visitas
            visits = negotiation.get("visits", [])
            if visits:
                for visit in visits:
                    visit_uid = visit.get("visitUID")
                    attended_name = visit.get("attendedName")
                    visit_number = visit.get("visitNumber")
                    latitude = visit.get("latitude")
                    longitude = visit.get("longitude")
                    visit_note = visit.get("visitnote")
                    concerns = visit.get("concerns")
                    next_steps = visit.get("nextSteps")
                    visitdate = visit.get("visitdate")
                    opportunities = visit.get("opportunities")
                    visittype_uid = visit.get("visittypeUID")
                    attendancetype_uid = visit.get("attendancetypeUID")
                    satisfaction_uid = visit.get("satisfactionUID")
                    visit_createuserid = visit.get("visitcreateuserid")
                    visit_createdate = visit.get("visitcreatedate")
                    visit_isactive = visit.get("visitisactive")
                    visit_issynchronized = visit.get("visitissynchronized")

                    if not any([visit_uid, visit_number, visittype_uid, attendancetype_uid]):
                        continue

                    visit_uid = visit_uid.strip() if visit_uid else None
                    attended_name = attended_name.strip() if attended_name else None
                    visit_number = int(visit_number) if visit_number and isinstance(visit_number, str) and visit_number.isdigit() else visit_number
                    latitude = float(latitude) if latitude and latitude not in [None, 'null', ''] else None
                    longitude = float(longitude) if longitude and longitude not in [None, 'null', ''] else None
                    visit_note = visit_note.strip() if visit_note else None
                    concerns = concerns.strip() if concerns else None
                    visitdate = visitdate.strip()
                    next_steps = next_steps.strip() if next_steps else None
                    opportunities = opportunities.strip() if opportunities else None
                    visittype_uid = visittype_uid.strip() if visittype_uid else None
                    attendancetype_uid = attendancetype_uid.strip() if attendancetype_uid else None
                    satisfaction_uid = satisfaction_uid.strip() if satisfaction_uid else None
                    visit_createuserid = int(visit_createuserid) if isinstance(visit_createuserid, str) and visit_createuserid.isdigit() else visit_createuserid
                    visit_createdate = visit_createdate.strip() if visit_createdate else None
                    visit_isactive = int(visit_isactive) if isinstance(visit_isactive, str) and visit_isactive.isdigit() else visit_isactive
                    visit_issynchronized = int(visit_issynchronized) if isinstance(visit_issynchronized, str) and visit_issynchronized.isdigit() else visit_issynchronized

                    if visit_issynchronized == 0:
                        query_check_visit = "SELECT COUNT(*) FROM visit WHERE visitUID = %s"
                        cursor.execute(query_check_visit, (visit_uid,))
                        exists_visit = cursor.fetchone()[0]

                        if exists_visit:
                            query_update_visit = """
                                UPDATE visit
                                SET attendedName = %s, visitNumber = %s, latitude = %s, longitude = %s, note = %s, concerns = %s, nextSteps = %s, opportunities = %s, visittypeUID = %s, attendancetypeUID = %s, satisfactionUID = %s, createuserid = %s, createdate = NOW(), isActive = %s, negotiationUID = %s
                                WHERE visitUID = %s
                            """

                            values_update_visit = (
                                attended_name, visit_number, latitude, longitude,
                                visit_note, concerns, next_steps, opportunities, visittype_uid,
                                attendancetype_uid, satisfaction_uid, visit_createuserid,
                                visit_isactive, negotiation_uid, visit_uid
                            )

                            cursor.execute(query_update_visit, values_update_visit)
                        else:
                            # Configure o logger
                            logging.basicConfig(level=logging.INFO)


                            # Definindo a consulta de inserção e os valores
                            query_insert_visit = """
                                INSERT INTO visit (visitUID, attendedName, visitNumber, latitude, longitude, note, concerns, nextSteps, opportunities, visittypeUID, attendancetypeUID, satisfactionUID, createuserid, createdate, isActive, negotiationUID, visitdate)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
                            """
                            values_insert_visit = (
                                visit_uid, attended_name, visit_number, latitude, longitude,
                                visit_note, concerns, next_steps, opportunities, visittype_uid,
                                attendancetype_uid, satisfaction_uid, visit_createuserid,
                                visit_createdate, visit_isactive, negotiation_uid, visitdate
                            )

                            # Imprimindo os valores no log
                            logging.info("Executando INSERT na tabela visit com os seguintes valores:")
                            logging.info("visitUID: %s", visit_uid)
                            logging.info("attendedName: %s", attended_name)
                            logging.info("visitNumber: %s", visit_number)
                            logging.info("latitude: %s", latitude)
                            logging.info("longitude: %s", longitude)
                            logging.info("note: %s", visit_note)
                            logging.info("concerns: %s", concerns)
                            logging.info("nextSteps: %s", next_steps)
                            logging.info("opportunities: %s", opportunities)
                            logging.info("visittypeUID: %s", visittype_uid)
                            logging.info("attendancetypeUID: %s", attendancetype_uid)
                            logging.info("satisfactionUID: %s", satisfaction_uid)
                            logging.info("createuserid: %s", visit_createuserid)
                            logging.info("createdate: %s", visit_createdate)
                            logging.info("isActive: %s", visit_isactive)
                            logging.info("negotiationUID: %s", negotiation_uid)

                            # Executando o comando de inserção
                            cursor.execute(query_insert_visit, values_insert_visit)

                            # Capturando o retorno do banco
                            rows_affected = cursor.rowcount  # Número de linhas afetadas pelo INSERT

                            # Registrando o resultado no log
                            logging.info("INSERT executado com sucesso. Linhas afetadas: %d", rows_affected)

                        inserted_visits += 1

        # Confirma a transação
        connection.commit()

        # Verifica se o número de negociações e visitas inseridas corresponde ao esperado
        if inserted_negotiations == expected_negotiations and inserted_visits == expected_visits:
            return {"message": "Negociações e visitas inseridas/atualizadas com sucesso"}
        else:
            raise HTTPException(status_code=400, detail="O número de negociações ou visitas inseridas/atualizadas não corresponde ao esperado")
    except Exception as e:
        connection.rollback()
        # Em caso de erro, reverte a transação
        print("Erro:", str(e))  # Mostra a mensagem do erro
        print("Traceback completo:")
        traceback.print_exc()  # Mostra o stack trace no terminal

        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Fecha a conexão com o banco de dados
        cursor.close()
        connection.close()
@router.get("/get/permissions")
async def get_permissions(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # Valida o token
    await validate_token(credentials)

    # Conecta ao banco de dados
    connection = None
    cursor = None
    try:
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Executa a consulta
        query = """
        SELECT
            groupUID,
            cityUID,
            userId,
            createdate,
            createuserid,
            isActive
        FROM user_group_city
        """
        cursor.execute(query)
        results = cursor.fetchall()

        # Converte os resultados em formato JSON
        columns = [desc[0] for desc in cursor.description]  # Obter nomes das colunas

        formatted_results = []
        for row in results:
            row_dict = dict(zip(columns, row))
            # Converte todos os valores para string se não forem JSON serializáveis
            row_dict = {k: str(v) if not isinstance(v, (str, int, float, bool, list, dict)) else v for k, v in row_dict.items()}
            formatted_results.append(row_dict)

        return formatted_results  # FastAPI converte automaticamente para JSON

    except Exception as e:
        # Log do erro
        print(f"Error in get_permissions: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@router.get("/get/supporttables")
async def export_all_data(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):

    # Conecta ao banco de dados
    connection = None
    cursor = None

    try:
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Consultas para todas as tabelas
        tables = [
            "customertype",
            "closingforecast",
            "negotiationstatus",
            "customersource",
            "priority",
            "brand",
            "model",
            "group",          # Tabela que é uma palavra reservada
            "subgroup",
            "equipment",
            "visittype",
            "attendancetype",
            "satisfaction"
        ]

        data = {}
        for table in tables:
            # Construir a consulta dinamicamente com tabelas escapadas
            query = f"""
            SELECT
                `{table}UID` AS UID,
                description,
                isActive
            FROM `{table}`
            """
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]  # Obter nomes das colunas
            formatted_results = [dict(zip(columns, row)) for row in results]
            data[table] = formatted_results

        return data  # FastAPI converte automaticamente para JSON

    except Exception as e:
        # Log do erro
        print(f"Error in export_all_data: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@router.get("/get/companyequipment")
async def get_company_equipment(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # Valida o token
    await validate_token(credentials)

    # Conecta ao banco de dados
    connection = None
    cursor = None
    try:
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Executa a consulta
        query = """
        SELECT
            companyequipmentUID,
            modelUID,
            brandUID,
            subgroupUID,
            groupUID,
            isActive
        FROM companyequipment
        """
        cursor.execute(query)
        results = cursor.fetchall()

        # Converte os resultados em formato JSON
        columns = [desc[0] for desc in cursor.description]  # Obter nomes das colunas
        formatted_results = [dict(zip(columns, row)) for row in results]

        return formatted_results  # FastAPI converte automaticamente para JSON

    except Exception as e:
        # Log do erro
        print(f"Error in get_company_equipment: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@router.get("/get/users")
async def get_users(credentials: HTTPAuthorizationCredentials = Depends(security)):
    # Valida o token
    await validate_token(credentials)

    connection = None
    cursor = None
    try:
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Executa a consulta
        query = """
        SELECT
            id,
            `name`,
            document,
            birthdate,
            email,
            `password`,
            passwordVersion,
            isRoot,
            createdate,
            createuserid,
            isActive
        FROM users
        """
        cursor.execute(query)
        results = cursor.fetchall()

        # Obter nomes das colunas
        columns = [desc[0] for desc in cursor.description]

        formatted_results = []
        for row in results:
            row_dict = dict(zip(columns, row))

            # Converte todos os valores para string se não forem JSON serializáveis
            row_dict = {
                k: str(v) if not isinstance(v, (str, int, float, bool, list, dict, type(None))) else v
                for k, v in row_dict.items()
            }

            formatted_results.append(row_dict)

        return formatted_results  # FastAPI converte automaticamente para JSON

    except Exception as e:
        # Log do erro
        print(f"Error in get_users: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()




@router.get("/get/customers")
async def get_customers(
        created_after: str,
       credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # Valida o token
    await validate_token(credentials)
    #print(created_after)

    # Conecta ao banco de dados
    connection = None
    cursor = None
    try:
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Executa a consulta com o filtro de data
        query = """
        SELECT
            customer.customerUID,
            customer.name,
            customer.document,
            customer.addressUID,
            customer.customertypeUID,
            customer.equipmentUID,
            customer.createdate AS customercreatedate,
            customer.createuserid AS customercreateuserid,
            customer.isActive AS customerisactive,
            equipment.equipmentUID,
            equipment.description AS equipmentdescription,
            equipment.createdate AS equipmentcreatedate,
            equipment.createuserid AS equipmentcreateuserid,
            equipment.isActive AS equipmentisactive,
            address.addressUID,
            address.description AS addressdescription,
            address.neighborhood,
            address.number,
            address.complement,
            address.cityUID,
            address.createdate AS addresscreatedate,
            address.createuserid AS addresscreateuserid,
            address.isActive AS addressisactive,
            GROUP_CONCAT(contact.contactUID) AS contactUID,
            GROUP_CONCAT(contact.responsible) AS responsible,
            GROUP_CONCAT(COALESCE(contact.phone, '0')) AS phone,
            GROUP_CONCAT(COALESCE(contact.email, '0')) AS email,
            GROUP_CONCAT(COALESCE(contact.createdate, '0')) AS contactcreatedate,
            GROUP_CONCAT(COALESCE(contact.createuserid, '0')) AS contactcreateuserid,
            GROUP_CONCAT(COALESCE(contact.isActive, '0')) AS contactisactive
        FROM customer
        JOIN address ON customer.addressUID = address.addressUID
        JOIN customer_has_contact ON customer_has_contact.customerUID = customer.customerUID
        JOIN contact ON contact.contactUID = customer_has_contact.contactUID
        LEFT JOIN equipment ON equipment.equipmentUID = customer.equipmentUID
        WHERE customer.createdate > %s
        GROUP BY customer.customerUID
        """

        cursor.execute(query, (created_after,))
        results = cursor.fetchall()

        # Obter nomes das colunas
        columns = [desc[0] for desc in cursor.description]

        # Converte os resultados em formato JSON
        formatted_results = []
        for row in results:
            row_dict = dict(zip(columns, row))
            row_dict = {k: str(v) if not isinstance(v, (str, int, float, bool, list, dict)) else v for k, v in
                        row_dict.items()}
            formatted_results.append(row_dict)

        # Adiciona o total de linhas exportadas
        exported_rows = len(formatted_results)

        return {
            "data": formatted_results,
            "exported_rows": exported_rows
        }

    except Exception as e:
        print(f"Error in get_customers: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()



@router.get("/get/negotiationsandvisits")
async def get_negotiations_and_visits(
        created_after: str,
        credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # Valida o token
    await validate_token(credentials)

    # Conecta ao banco de dados
    connection = None
    cursor = None
    try:
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Executa a consulta principal com o filtro de data
        query = """
        SELECT 
            negotiation.negotiationUID,
            negotiation.customerUID,
            negotiation.closingforecastUID,
            negotiation.negotiationstatusUID,
            negotiation.customersourceUID,
            negotiation.priorityUID,
            negotiation.note,
            negotiation.negotiationdate,
            negotiation.createdate as negotiationcreatedate,
            negotiation.createuserid as negotiationcreateuserid,
            negotiation.isActive as negotiationisactive,
            visit.visitUID,
            visit.attendedName,
            visit.visitNumber,
            visit.latitude,
            visit.negotiationUID as visitnegotiationuid,
            visit.longitude,
            visit.note as visitnote,
            visit.visitdate,
            visit.concerns,
            visit.nextSteps,
            visit.opportunities,
            visit.visittypeUID,
            visit.attendancetypeUID,
            visit.satisfactionUID,
            visit.isactive as visitisactive,
            visit.createuserid as visitcreateuserid,
            visit.createdate as visitcreatedate,
            GROUP_CONCAT(companyequipment_has_negotiation.companyequipmentUID) as companyequipmentUID,
            GROUP_CONCAT(COALESCE(companyequipment_has_negotiation.value, '0')) AS companyequipmentvalue,
            GROUP_CONCAT(COALESCE(companyequipment_has_negotiation.quantity, '0')) AS companyequipmentquantity
        FROM negotiation
        LEFT JOIN visit ON visit.negotiationUID = negotiation.negotiationUID
        LEFT JOIN companyequipment_has_negotiation ON companyequipment_has_negotiation.negotiationUID = negotiation.negotiationUID
        WHERE negotiation.createdate > %s
        GROUP BY negotiation.negotiationUID, visit.visitUID
        """

        cursor.execute(query, (created_after,))
        results = cursor.fetchall()

        # Obter nomes das colunas
        columns = [desc[0] for desc in cursor.description]

        # Contar o número de negociações distintas e visitas
        distinct_negotiations_query = """
        SELECT COUNT(DISTINCT negotiation.negotiationUID)
        FROM negotiation
        WHERE negotiation.createdate > %s
        """
        cursor.execute(distinct_negotiations_query, (created_after,))
        num_negotiations = cursor.fetchone()[0]

        num_visits = len(set(row[columns.index('visitUID')] for row in results if row[columns.index('visitUID')] is not None))

        # Converte os resultados em formato JSON
        formatted_results = []
        for row in results:
            row_dict = dict(zip(columns, row))
            row_dict = {k: str(v) if not isinstance(v, (str, int, float, bool, list, dict)) else v for k, v in
                        row_dict.items()}
            formatted_results.append(row_dict)

        return {
            "data": formatted_results,
            "exported_negotiations": num_negotiations,
            "exported_visits": num_visits
        }

    except Exception as e:
        print(f"Error in get_negotiations_and_visits: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
    #a partir aqui pra baixo é a aPI do site grasellersappp

@router.get("/get/permissions123")
async def get_permissions():
    # Conecta ao banco de dados
    connection = None
    cursor = None
    try:
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Executa a consulta SQL para obter as permissões
        query = """
        SELECT 
            `group`.description AS Grupo, 
            users.name AS Vendedor, 
            city.description AS Cidade
        FROM user_group_city
        JOIN users ON users.id = user_group_city.userid
        JOIN city ON city.cityuid = user_group_city.cityUID
        JOIN `group` ON `group`.groupUID = user_group_city.groupUID
        ORDER BY users.name, `group`.description, city.description
        """
        cursor.execute(query)
        results = cursor.fetchall()

        # Converte os resultados em formato JSON
        columns = [desc[0] for desc in cursor.description]  # Obter nomes das colunas
        formatted_results = [dict(zip(columns, row)) for row in results]

        return formatted_results  # FastAPI converte automaticamente para JSON

    except Exception as e:
        # Log do erro
        print(f"Error in get_permissions: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@router.post("/post/edit/supporttables")
async def edit_support_table(
        body: dict = Body(...),  # Recebe o JSON completo no corpo
):
    # Log do corpo da requisição
    print("Body da requisição:", body)

    # Extraindo os parâmetros do corpo
    supporttable = body.get('supporttable')  # Obter o parâmetro supporttable do corpo
    olddescription = body.get('olddescription')
    newdescription = body.get('newdescription')
    isActive = body.get('isActive')

    # Validação do parâmetro supporttable
    if not supporttable:
        raise HTTPException(status_code=400, detail="Missing supporttable in body")

    # Validação dos parâmetros no corpo
    if not olddescription or not newdescription or isActive is None:
        raise HTTPException(status_code=400, detail="Missing required body parameters")

    # Converte isActive de string para inteiro
    if isActive == "sim":
        isActive = 1
    elif isActive == "nao":
        isActive = 0
    else:
        raise HTTPException(status_code=400, detail="Invalid value for isActive. Must be 'Sim' or 'Não'.")

    # Conecta ao banco de dados
    connection = None
    cursor = None
    try:
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Query para editar a tabela de suporte com base na olddescription
        query = f"""
        UPDATE {supporttable}
        SET description = %s, isActive = %s
        WHERE description = %s
        """
        values = (newdescription, isActive, olddescription)

        cursor.execute(query, values)
        connection.commit()

        return {"message": f"Support table '{supporttable}' updated successfully"}

    except Exception as e:
        # Log do erro
        print(f"Error in edit_support_table: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@router.post("/post/edit/companyequipments")
async def edit_company_equipments(
        body: dict = Body(...),  # Recebe o JSON completo no corpo
):
    # Log do corpo da requisição
    print("Body da requisição:", body)

    # Extraindo os parâmetros do corpo
    oldBrandDescription = body.get('oldBrandDescription')
    oldGroupDescription = body.get('oldGroupDescription')
    oldSubgroupDescription = body.get('oldSubgroupDescription')
    oldModelDescription = body.get('oldModelDescription')
    oldIsActive = body.get('oldIsActive')
    newModelDescription = body.get('newModelDescription')
    newBrandDescription = body.get('newBrandDescription')
    newSubgroupDescription = body.get('newSubgroupDescription')
    newGroupDescription = body.get('newGroupDescription')
    newIsActive = body.get('newIsActive')

    # Validação dos parâmetros no corpo
    if not all([oldBrandDescription, oldGroupDescription, oldSubgroupDescription,
                oldModelDescription, oldIsActive, newModelDescription,
                newBrandDescription, newSubgroupDescription, newGroupDescription, newIsActive]):
        raise HTTPException(status_code=400, detail="Missing required body parameters")

    # Converte oldIsActive e newIsActive de string para inteiro, se necessário
    oldIsActive = 1 if oldIsActive.lower() == "sim" else 0
    newIsActive = 1 if newIsActive.lower() == "sim" else 0

    # Conecta ao banco de dados
    connection = None
    cursor = None
    try:
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Query para editar a tabela companyequipment
        query = """
UPDATE companyequipment
SET 
    modelUID = (SELECT modelUID FROM model WHERE description = %s),
    brandUID = (SELECT brandUID FROM brand WHERE description = %s),
    subgroupUID = (SELECT subgroupUID FROM subgroup WHERE description = %s),
    groupUID = (SELECT groupUID FROM `group` WHERE description = %s),
    isActive = %s
WHERE 
    brandUID = (SELECT brandUID FROM brand WHERE description = %s) AND
    groupUID = (SELECT groupUID FROM `group` WHERE description = %s) AND
    subgroupUID = (SELECT subgroupUID FROM subgroup WHERE description = %s) AND
    modelUID = (SELECT modelUID FROM model WHERE description = %s) AND
    isActive = %s;
        """
        values = (
            newModelDescription,
            newBrandDescription,
            newSubgroupDescription,
            newGroupDescription,
            newIsActive,
            oldBrandDescription,
            oldGroupDescription,
            oldSubgroupDescription,
            oldModelDescription,
            oldIsActive
        )

        cursor.execute(query, values)
        connection.commit()

        return {"message": "Company equipment updated successfully"}

    except Exception as e:
        # Log do erro
        print(f"Error in edit_company_equipments: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@router.post("/post/edit/permissions")
async def edit_company_equipment(
        body: dict = Body(...),  # Recebe o JSON completo no corpo
):
    # Log do corpo da requisição
    print("Body da requisição:", body)

    # Extraindo os parâmetros do corpo
    oldGroupDescription = body.get('oldGroupDescription')
    oldUserName = body.get('oldUserName')
    oldCityName = body.get('oldCityName')
    newGroupDescription = body.get('newGroupDescription')
    newUserName = body.get('newUserName')
    newCityName = body.get('newCityName')

    # Validação dos parâmetros no corpo
    if not all([oldGroupDescription, oldUserName, oldCityName,
                newGroupDescription, newUserName,
                newCityName]):
        raise HTTPException(status_code=400, detail="Missing required body parameters")


    # Conecta ao banco de dados
    connection = None
    cursor = None
    try:
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Query para editar a tabela companyequipment
        query = """
        UPDATE user_group_city
        SET 
            groupUID = (SELECT groupUID FROM `group` WHERE description = %s),
            userid = (SELECT id FROM users WHERE name = %s),
            cityUID = (SELECT cityUID FROM city WHERE description = %s)
         
        WHERE 
            groupUID = (SELECT groupUID FROM `group` WHERE description = %s) AND
            userId = (SELECT id FROM users WHERE name = %s) AND 
            cityUID = (SELECT cityUID FROM city WHERE description = %s)

        """
        values = (
            newGroupDescription,
            newUserName,
            newCityName,
            oldGroupDescription,
            oldUserName,
            oldCityName

        )

        cursor.execute(query, values)
        connection.commit()

        return {"message": "Company equipment updated successfully"}

    except Exception as e:
        # Log do erro
        print(f"Error in edit_company_equipment: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@router.post("/post/add/companyequipments")
async def add_company_equipments(
        body: dict = Body(...),  # Recebe o JSON completo no corpo
):
    # Log do corpo da requisição
    print("Body da requisição:", body)

    # Extraindo os parâmetros do corpo
    newModelDescription = body.get('newModelDescription')
    newBrandDescription = body.get('newBrandDescription')
    newSubgroupDescription = body.get('newSubgroupDescription')
    newGroupDescription = body.get('newGroupDescription')
    newIsActive = body.get('newIsActive')

    # Validação dos parâmetros no corpo
    if not all([newModelDescription, newBrandDescription, newSubgroupDescription,
                newGroupDescription, newIsActive]):
        raise HTTPException(status_code=400, detail="Missing required body parameters")

    # Converte newIsActive de string para inteiro, se necessário
    newIsActive = 1 if newIsActive.lower() == "sim" else 0

    # Gera o companyequipmentUID
    companyequipmentUID = str(uuid.uuid4()).upper()  # Gera um UUID e transforma em maiúsculo

    # Conecta ao banco de dados
    connection = None
    cursor = None
    try:
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Query para obter os UIDs
        query = """
        SELECT
            (SELECT modelUID FROM model WHERE description = %s) AS modelUID,
            (SELECT brandUID FROM brand WHERE description = %s) AS brandUID,
            (SELECT subgroupUID FROM subgroup WHERE description = %s) AS subgroupUID,
            (SELECT groupUID FROM `group` WHERE description = %s) AS groupUID;
        """
        values = (newModelDescription, newBrandDescription, newSubgroupDescription, newGroupDescription)
        cursor.execute(query, values)
        result = cursor.fetchone()

        if result is None:
            raise HTTPException(status_code=404, detail="One or more descriptions not found")

        modelUID, brandUID, subgroupUID, groupUID = result

        # Verifica se os UIDs foram encontrados
        if any(uid is None for uid in [modelUID, brandUID, subgroupUID, groupUID]):
            raise HTTPException(status_code=404, detail="One or more UIDs not found")

        # Query para inserir na tabela companyequipment
        insert_query = """
        INSERT INTO companyequipment (companyequipmentUID, modelUID, brandUID, subgroupUID, groupUID, createdate, createuserid, isActive)
        VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s);
        """
        insert_values = (companyequipmentUID, modelUID, brandUID, subgroupUID, groupUID, 1, newIsActive)

        cursor.execute(insert_query, insert_values)
        connection.commit()

        return {"message": "Company equipment added successfully", "companyequipmentUID": companyequipmentUID}

    except Exception as e:
        # Log do erro
        print(f"Error in add_company_equipments: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@router.post("/post/add/permissions")
async def add_permissions(
    body: dict = Body(...),  # Recebe o JSON completo no corpo
):
    # Log do corpo da requisição
    print("Body da requisição:", body)

    # Extraindo os parâmetros do corpo
    group = body.get('group')
    city = body.get('city')
    seller = body.get('seller')

    # Log dos parâmetros extraídos
    print(f"Parâmetros recebidos - Grupo: {group}, Cidade: {city}, Vendedor: {seller}")

    # Validação dos parâmetros no corpo
    if not all([group, city, seller]):
        print("Erro: Parâmetros obrigatórios ausentes")
        raise HTTPException(status_code=400, detail="Missing required body parameters")

    # Conecta ao banco de dados
    connection = None
    cursor = None
    try:
        print("Conectando ao banco de dados...")
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Query para obter os UIDs
        query = """
        SELECT
            (SELECT groupUID FROM `group` WHERE description = %s) AS groupUID,
            (SELECT cityUID FROM city WHERE description = %s) AS cityUID,
            (SELECT id FROM users WHERE name = %s) AS userID;
        """
        values = (group, city, seller)
        print("Executando query para obter UIDs:", values)
        cursor.execute(query, values)
        result = cursor.fetchone()

        print("Resultado da query UIDs:", result)
        if result is None:
            print("Erro: Uma ou mais descrições não foram encontradas")
            raise HTTPException(status_code=404, detail="One or more descriptions not found")

        groupUID, cityUID, userID = result

        # Verifica se os UIDs foram encontrados
        if any(uid is None for uid in [groupUID, cityUID, userID]):
            print("Erro: Um ou mais UIDs não foram encontrados")
            raise HTTPException(status_code=404, detail="One or more UIDs not found")

        # Query para inserir na tabela user_group_city
        insert_query = """
        INSERT INTO user_group_city (groupUID, cityUID, userid, createdate, createuserid, isActive)
        VALUES (%s, %s, %s, NOW(), %s, %s);
        """
        insert_values = (groupUID, cityUID, userID, 1, 1)  # createdate usa NOW(), createuserid = 1, isActive = 1

        print("Executando query de inserção:", insert_values)
        cursor.execute(insert_query, insert_values)
        connection.commit()

        print("Inserção bem-sucedida")
        return {"message": "Permission added successfully"}

    except Exception as e:
        # Log do erro
        print(f"Error in add_permissions: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
        print("Conexão ao banco de dados fechada")

@router.post("/post/delete/permissions")
async def delete_permissions(
    body: dict = Body(...),  # Recebe o JSON completo no corpo
):
    # Log do corpo da requisição
    print("Body da requisição:", body)

    # Extraindo os parâmetros do corpo
    group = body.get('group')
    city = body.get('city')
    seller = body.get('seller')

    # Log dos parâmetros extraídos
    print(f"Parâmetros recebidos - Grupo: {group}, Cidade: {city}, Vendedor: {seller}")

    # Validação dos parâmetros no corpo
    if not all([group, city, seller]):
        print("Erro: Parâmetros obrigatórios ausentes")
        raise HTTPException(status_code=400, detail="Missing required body parameters")

    # Conecta ao banco de dados
    connection = None
    cursor = None
    try:
        print("Conectando ao banco de dados...")
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Query para deletar na tabela user_group_city
        delete_query = """
        DELETE FROM user_group_city
        WHERE groupUID = (SELECT groupUID FROM `group` WHERE description = %s)
        AND cityUID = (SELECT cityUID FROM city WHERE description = %s)
        AND userid = (SELECT id FROM users WHERE name = %s);
        """
        values = (group, city, seller)
        print("Executando query de exclusão:", values)
        cursor.execute(delete_query, values)
        connection.commit()

        # Verifica se alguma linha foi afetada
        if cursor.rowcount == 0:
            print("Nenhum registro encontrado para exclusão")
            raise HTTPException(status_code=404, detail="No matching records found")

        print("Exclusão bem-sucedida")
        return {"message": "Permission deleted successfully"}

    except Exception as e:
        # Log do erro
        print(f"Error in delete_permissions: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
        print("Conexão ao banco de dados fechada")

@router.post("/post/add/supporttables")
async def add_support_table(
        body: dict = Body(...),  # Recebe o JSON completo no corpo
):
    # Log do corpo da requisição
    print("Body da requisição:", body)

    # Extraindo os parâmetros do corpo
    supporttable = body.get('supporttable')  # Obter o parâmetro supporttable do corpo
    description = body.get('newdescription')  # Obter a nova descrição
    isActive = body.get('isActive')  # Obter o status de ativo

    # Validação do parâmetro supporttable
    if not supporttable:
        raise HTTPException(status_code=400, detail="Missing supporttable in body")

    # Validação dos parâmetros no corpo
    if not description or isActive is None:
        raise HTTPException(status_code=400, detail="Missing required body parameters")

    # Converte isActive de string para inteiro
    if isActive == "sim":
        isActive = 1
    elif isActive == "nao":
        isActive = 0
    else:
        raise HTTPException(status_code=400, detail="Invalid value for isActive. Must be 'Sim' or 'Não'.")

    # Gera um UUID aleatório
    uid = str(uuid.uuid4())  # Converte o UUID gerado para string

    # Conecta ao banco de dados
    connection = None
    cursor = None
    try:
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Nome do campo de chave primária
        primary_key_field = f"{supporttable}UID"

        # Remove crases se o campo primário for 'groupUID'
        if primary_key_field == "`group`UID":
            primary_key_field = "groupUID"  # Mantém sem crases
        else:
            primary_key_field = primary_key_field

        # Query para inserir na tabela de suporte
        query = f"""
        INSERT INTO {supporttable} ({primary_key_field}, description, createDate, createUserId, isActive)
        VALUES (%s, %s, NOW(), %s, %s)
        """
        values = (uid, description, 1, isActive)  # 1 para createUserId como solicitado

        cursor.execute(query, values)
        connection.commit()

        return {"message": f"New record added to support table '{supporttable}' successfully with {primary_key_field} '{uid}'"}

    except Exception as e:
        # Log do erro
        print(f"Error in add_support_table: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@router.get("/get/supporttables123")
async def export_all_data():

    # Conecta ao banco de dados

    connection = None
    cursor = None

    try:
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Consultas para todas as tabelas
        tables = [
            "customertype",
            "closingforecast",
            "negotiationstatus",
            "customersource",
            "priority",
            "brand",
            "model",
            "group",          # Tabela que é uma palavra reservada
            "subgroup",
            "equipment",
            "visittype",
            "attendancetype",
            "satisfaction"
        ]

        data = {}
        for table in tables:
            # Construir a consulta dinamicamente com tabelas escapadas
            query = f"""
            SELECT
                `{table}UID` AS UID,
                description,
                isActive
            FROM `{table}`
            ORDER BY description
            """
            cursor.execute(query)
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]  # Obter nomes das colunas
            formatted_results = [dict(zip(columns, row)) for row in results]
            data[table] = formatted_results

        return data  # FastAPI converte automaticamente para JSON

    except Exception as e:
        # Log do erro
        print(f"Error in export_all_data: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@router.get("/get/companyequipments")
async def get_company_equipments(
):

    # Conecta ao banco de dados
    connection = None
    cursor = None
    try:
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Executa a nova consulta
        query = """
        SELECT 
            brand.description AS Marca, 
            `group`.description AS Grupo, 
            subgroup.description AS Subgrupo, 
            model.description AS Modelo, 
            CASE 
                WHEN companyequipment.isActive = 1 THEN 'Sim'
                ELSE 'Não'
            END AS Ativo
        FROM companyequipment
        JOIN brand ON brand.brandUID = companyequipment.brandUID
        JOIN `group` ON `group`.groupUID = companyequipment.groupUID
        JOIN subgroup ON subgroup.subgroupUID = companyequipment.subgroupUID
        JOIN model ON model.modelUID = companyequipment.modelUID
        ORDER BY brand.description, `group`.description, subgroup.description, model.description
        """
        cursor.execute(query)
        results = cursor.fetchall()

        # Converte os resultados em formato JSON
        columns = [desc[0] for desc in cursor.description]  # Obter nomes das colunas
        formatted_results = [dict(zip(columns, row)) for row in results]

        return formatted_results  # FastAPI converte automaticamente para JSON

    except Exception as e:
        # Log do erro
        print(f"Error in get_company_equipments: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


@router.get("/get/web/users")
async def get_users():
    # Conecta ao banco de dados
    connection = None
    cursor = None

    try:
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Consulta para a tabela users
        query = """
        SELECT name as Vendedor, isActive
        FROM users
        ORDER BY name
        """
        cursor.execute(query)
        results = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]  # Obter nomes das colunas
        formatted_results = [dict(zip(columns, row)) for row in results]

        return formatted_results  # FastAPI converte automaticamente para JSON

    except Exception as e:
        # Log do erro
        print(f"Error in get_users: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@router.post("/upload-pdf/")
async def upload_pdf(
    file: UploadFile = File(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),  # Obter credenciais
):
    # Validar o token antes de continuar
    await validate_token(credentials)

    try:
        print("Entrou na função upload_pdf")

        # Verifique se o arquivo é um PDF
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="O arquivo não é um PDF")

        print(f"Recebendo arquivo: {file.filename}")

        # Salvar o arquivo PDF no servidor
        result = await save_file_async(file)

        if result["message"] == "Arquivo enviado com sucesso":
            return {"message": "PDF enviado com sucesso"}
        else:
            raise HTTPException(status_code=500, detail="Falha ao salvar o arquivo")

    except HTTPException as http_exc:
        raise http_exc  # Relevante para erros HTTP esperados
    except Exception as e:
        print(f"Erro durante o processamento: {e}")
        raise HTTPException(status_code=500, detail="Erro interno do servidor")


# Função para salvar o arquivo PDF
async def save_file_async(file: UploadFile):
    try:
        # Defina o caminho para a pasta de destino
        pasta_destino = r"\\srv-zada\gra\Pedidos"

        # Certifique-se de que a pasta de destino existe
        if not os.path.exists(pasta_destino):
            print(f"Pasta de destino não existe: {pasta_destino}")
            os.makedirs(pasta_destino)

        # Salve o arquivo na pasta destino
        destino_arquivo = os.path.join(pasta_destino, file.filename)
        print(f"Salvando arquivo em: {destino_arquivo}")

        async with aiofiles.open(destino_arquivo, "wb") as buffer:
            await buffer.write(await file.read())

        print("Arquivo enviado com sucesso")
        return {"message": "Arquivo enviado com sucesso", "file_path": destino_arquivo}
    except Exception as e:
        print(f"Erro durante o processamento: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/get/maquinasPatio")
async def get_maquinas_patio(
        #credentials: HTTPAuthorizationCredentials = Depends(security),
):
    try:
        # Valida o token
        #await validate_token(credentials)

        # Chama a função de processamento
        processed_data = process_excel_data()

        # Adapta os dados para o formato JSON
        json_data = jsonable_encoder(processed_data)

        # Retorna os dados processados no formato JSON
        return json_data
    except Exception as e:
        # Caso haja um erro de validação ou outro erro, retorne um erro 401 (não autorizado)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )


# --- Endpoint GET ---
class VendedorInput(BaseModel):
    vendedor: str

# --- Endpoint GET ---
class VendedorInput(BaseModel):
    vendedor: str

@router.get("/get/municipiosVendedor")
async def get_municipios_vendedor(vendedor: str = Query(..., description="Nome do vendedor")):
    try:
        vendedor_input = vendedor.strip().upper()

        # Conecta ao banco
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Executa a stored procedure
        cursor.callproc("grasellers.VendedorPorMunicipio")

        # Lê resultados
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        data = [dict(zip(columns, row)) for row in result]

        cursor.close()
        connection.close()

        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nenhum dado retornado da procedure"
            )

        # Normaliza lista de vendedores
        vendedores_lista = [(row.get("vendedor") or "").strip().upper() for row in data]

        # 1º Tentativa: matching direto por "começa com"
        vendedor_match = None
        for vend in vendedores_lista:
            if vend.startswith(vendedor_input):
                vendedor_match = vend
                break

        # 2º Tentativa: similaridade (difflib)
        if not vendedor_match:
            matches = get_close_matches(vendedor_input, vendedores_lista, n=1, cutoff=0.6)
            if matches:
                vendedor_match = matches[0]

        if not vendedor_match:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Vendedor '{vendedor}' não encontrado"
            )

        # Filtra todas as linhas do vendedor encontrado
        linhas_vendedor = [
            row for row in data
            if (row.get("vendedor") or "").strip().upper() == vendedor_match
        ]

        # Extrai apenas os municípios (ignorando TOTAL)
        municipios = []
        for row in linhas_vendedor:
            municipio = (row.get("municipio") or "").strip()
            if municipio.upper().startswith("TOTAL"):
                continue
            municipios.append(municipio)

        if not municipios:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nenhum município encontrado para o vendedor '{vendedor}'"
            )

        return {
            "vendedor_informado": vendedor,
            "vendedor_encontrado": vendedor_match,
            "municipios": municipios
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar requisição: {str(e)}"
        )


@router.get("/get/vendedorPorMunicipio")
async def get_vendedor_por_municipio(
    municipio: str = Query(..., description="Nome do município a ser consultado")
):
    try:
        municipio_input = municipio.strip().upper()

        # Conecta ao banco
        connection = database.connect_to_database()
        cursor = connection.cursor()

        # Executa a stored procedure
        cursor.callproc("grasellers.VendedorPorMunicipio")

        # Recupera os resultados
        result = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        data = [dict(zip(columns, row)) for row in result]

        cursor.close()
        connection.close()

        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nenhum dado retornado da procedure"
            )

        # Procura o município informado
        for row in data:
            municipio_row = (row.get("municipio") or "").strip().upper()
            if municipio_input == municipio_row:
                vendedor = row.get("vendedor")
                return jsonable_encoder({
                    "municipio": municipio,
                    "vendedor": vendedor
                })

        # Caso não encontre
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Município '{municipio}' não encontrado"
        )

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao processar requisição: {str(e)}"
        )
