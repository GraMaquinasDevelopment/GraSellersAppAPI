import datetime
import json
import os
from typing import List, Dict
from venv import logger

import jwt
from fastapi import APIRouter, HTTPException, Depends, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import database  # Certifique-se de que o módulo database está implementado corretamente

router = APIRouter()
security = HTTPBearer()


# Obtém a SECRET_KEY da variável de ambiente
SECRET_KEY = "1e255487c1c756ce12133c0762a16fe5779ca1d313470369436f32c2190f56d08eeb0aced2217aeba658a246ac773d01392478e341e56ee1c68a343270d38dfd"
ALGORITHM = "HS256"

async def validate_token(credentials: HTTPAuthorizationCredentials):
    token = credentials.credentials
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

            # Verificar se todos os campos têm o mesmo número de registros
            if not (len(responsibles) == len(phones) == len(emails) == len(contactcreateuserids) == len(contactisactives) == num_contacts):
                raise HTTPException(status_code=400, detail="Dados de contato inconsistentes")

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
            logger.info(f"total_inserts: {total_inserts}")
            logger.info(f"expected_inserts: {expected_inserts}")
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
            negotiation_createdate = negotiation.get("negotiationcreatedate")
            negotiation_createuserid = negotiation.get("negotiationcreateuserid")
            negotiation_isactive = negotiation.get("negotiationisactive")
            negotiation_issynchronized = negotiation.get("negotiationissynchronized")

            # Verifica se todos os campos obrigatórios estão presentes
            if not all([negotiation_uid, customer_uid, closingforecast_uid, negotiationstatus_uid, customersource_uid,
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
                        SET customerUID = %s, closingforecastUID = %s, negotiationstatusUID = %s, customersourceUID = %s,
                            priorityUID = %s, note = %s, createdate = NOW(), createuserid = %s, isActive = %s
                        WHERE negotiationUID = %s
                    """
                    values_update_negotiation = (
                        customer_uid, closingforecast_uid, negotiationstatus_uid,
                        customersource_uid, priority_uid, note,
                        negotiation_createuserid, negotiation_isactive, negotiation_uid
                    )
                    cursor.execute(query_update_negotiation, values_update_negotiation)
                else:
                    # Inserir nova negociação
                    query_insert_negotiation = """
                        INSERT INTO negotiation (negotiationUID, customerUID, closingforecastUID, negotiationstatusUID, customersourceUID, priorityUID, note, createdate, createuserid, isActive)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    values_insert_negotiation = (
                        negotiation_uid, customer_uid, closingforecast_uid, negotiationstatus_uid,
                        customersource_uid, priority_uid, note, negotiation_createdate,
                        negotiation_createuserid, negotiation_isactive
                    )
                    cursor.execute(query_insert_negotiation, values_insert_negotiation)

                inserted_negotiations += 1

                # Manipulação de companyequipment_has_negotiation
                company_equipment_uids = negotiation.get("companyequipmentUID", "")
                company_equipment_values = negotiation.get("companyequipmentvalue", "")

                if isinstance(company_equipment_uids, str) and isinstance(company_equipment_values, str):
                    company_equipment_uids = company_equipment_uids.split(",")
                    company_equipment_values = company_equipment_values.split(",")

                    # Deletar registros existentes
                    query_delete_companyequipment = """
                        DELETE FROM companyequipment_has_negotiation WHERE negotiationUID = %s
                    """
                    cursor.execute(query_delete_companyequipment, (negotiation_uid,))

                    for equipment_uid, value in zip(company_equipment_uids, company_equipment_values):
                        equipment_uid = equipment_uid.strip()
                        value = value.strip() if value.strip() else "0"

                        if equipment_uid:
                            query_insert_companyequipment = """
                                INSERT INTO companyequipment_has_negotiation (negotiationUID, companyequipmentUID, value)
                                VALUES (%s, %s, %s)
                            """
                            values_companyequipment = (negotiation_uid, equipment_uid, value)
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
                            query_insert_visit = """
                                INSERT INTO visit (visitUID, attendedName, visitNumber, latitude, longitude, note, concerns, nextSteps, opportunities, visittypeUID, attendancetypeUID, satisfactionUID, createuserid, createdate, isActive, negotiationUID)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """
                            values_insert_visit = (
                                visit_uid, attended_name, visit_number, latitude, longitude,
                                visit_note, concerns, next_steps, opportunities, visittype_uid,
                                attendancetype_uid, satisfaction_uid, visit_createuserid,
                                visit_createdate, visit_isactive, negotiation_uid
                            )
                            cursor.execute(query_insert_visit, values_insert_visit)

                        inserted_visits += 1

        # Confirma a transação
        connection.commit()

        # Verifica se o número de negociações e visitas inseridas corresponde ao esperado
        if inserted_negotiations == expected_negotiations and inserted_visits == expected_visits:
            return {"message": "Negociações e visitas inseridas/atualizadas com sucesso"}
        else:
            raise HTTPException(status_code=400, detail="O número de negociações ou visitas inseridas/atualizadas não corresponde ao esperado")
    except Exception as e:
        # Em caso de erro, reverte a transação
        connection.rollback()
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
    # Valida o token
    #await validate_token(credentials)

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
                description
            FROM `{table}`
            WHERE isActive = 1
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
            groupUID
        FROM companyequipment
        WHERE isActive = 1
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
        created_after: str
       #credentials: HTTPAuthorizationCredentials = Depends(security)
):
    # Valida o token
    #await validate_token(credentials)*/
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
            GROUP_CONCAT(COALESCE(companyequipment_has_negotiation.value, '0')) AS companyequipmentvalue
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