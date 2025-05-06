from flask import render_template, url_for, redirect, flash, request
from ims import app, db
from ims.forms import addproduct, addlocation, moveproduct  # Removed editproduct and editlocation
from ims.models import Location, Product, Movement, Balance
from sqlalchemy.exc import IntegrityError
import datetime

@app.route("/")

@app.route("/home")
def home():
    return render_template('home.html', title='Home')

@app.route("/Product", methods=['GET', 'POST'])
def product():
    form = addproduct()
    eform = None  
    details = Product.query.all()

    if not details and request.method == 'GET':
        flash('Add products to view', 'info')

    if request.method == 'POST':
        if eform and eform.validate_on_submit():
            pass  
        elif form.validate_on_submit():
            product = Product(prod_name=form.prodname.data, prod_qty=form.prodqty.data)
            db.session.add(product)
            try:
                db.session.commit()
                flash(f'Product {form.prodname.data} added!', 'success')
            except IntegrityError:
                db.session.rollback()
                flash('This product already exists', 'danger')
            return redirect(url_for('product'))

    return render_template('product.html', title='Products', form=form, eform=eform, details=details)


@app.route("/Product/<int:product_id>", methods=['GET', 'POST'])
def product_with_id(product_id):
    print(f"Product with ID route called with product_id: {product_id}")  # Debug log
    product = Product.query.get_or_404(product_id)
    form = addproduct()

    if request.method == 'POST' and form.validate_on_submit():
        product.prod_name = form.prodname.data
        product.prod_qty = form.prodqty.data
        try:
            db.session.commit()
            flash(f'Product {form.prodname.data} updated successfully!', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Error updating product. Please try again.', 'danger')
        return redirect(url_for('product'))

    return render_template('product.html', title='Edit Product', form=form, details=[product])


@app.route("/Location", methods=['GET', 'POST'])
def location():
    form = addlocation()
    locationform = None  
    details = Location.query.all()

    if not details and request.method == 'GET':
        flash('Add locations to view', 'info')

    if request.method == 'POST':
        if locationform and locationform.validate_on_submit():
            pass  # Removed the editlocation logic
        elif form.validate_on_submit():
            location = Location(loc_name=form.locname.data)  # Corrected field name
            db.session.add(location)
            try:
                db.session.commit()
                flash(f'Location {form.locname.data} added!', 'success')
            except IntegrityError:
                db.session.rollback()
                flash('This location already exists', 'danger')
            return redirect(url_for('location'))

    return render_template('location.html', title='Locations', form=form, locationform=locationform, details=details)

@app.route("/Location/edit_location/<int:location_id>", methods=['POST'])
def edit_location(location_id):
    print(f"Edit location route called with location_id: {location_id}")  # Debug log
    location = Location.query.get_or_404(location_id)
    form = addlocation()
    if form.validate_on_submit():
        location.loc_name = form.locname.data
        try:
            db.session.commit()
            flash(f'Location {form.locname.data} updated successfully!', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Error updating location. Please try again.', 'danger')
    return redirect(url_for('location'))


@app.route("/delete_location/<int:location_id>", methods=['POST'])
def delete_location(location_id):
    location = Location.query.get_or_404(location_id)
    try:
        db.session.delete(location)
        db.session.commit()
        flash(f'Location {location.loc_name} deleted successfully!', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('Error deleting location. Please try again.', 'danger')
    return redirect(url_for('location'))

@app.route("/Transfers", methods=['GET', 'POST'])
def move():
    form = moveproduct()
    
    movements = db.session.query(
        Movement.mid,
        Movement.ts,
        Movement.frm,
        Movement.to,
        Movement.pname,
        Movement.pqty
    ).order_by(Movement.ts.desc()).all()
    
    details = [{
        'mid': m.mid,
        'ts': m.ts,
        'frm': m.frm if m.frm else 'N/A',
        'to': m.to if m.to else 'N/A',
        'pname': m.pname,
        'pqty': m.pqty
    } for m in movements]

    products = Product.query.all()
    locations = Location.query.all()

    # Populate form choices
    form.mprodname.choices = [(p.prod_name, p.prod_name) for p in products]
    form.src.choices = [('---', '---')] + [(l.loc_name, l.loc_name) for l in locations]
    form.destination.choices = [('---', '---')] + [(l.loc_name, l.loc_name) for l in locations]

    if request.method == 'POST':
        movement_type = request.form.get('movement_type')
        if form.validate_on_submit():
            product_name = form.mprodname.data
            qty = form.mprodqty.data
            timestamp = datetime.datetime.now()

            # Handle different movement types
            if movement_type == 'Buy':
                frm = 'Supplier'
                to = 'Warehouse'
            elif movement_type == 'Sale':
                frm = 'Warehouse'
                to = 'Customer'
            else:  # Transfer
                frm = form.src.data
                to = form.destination.data
                if frm == '---' or to == '---':
                    flash('Both source and destination are required for transfer', 'danger')
                    return redirect(url_for('move'))
                if frm == to:
                    flash('Source and destination cannot be the same', 'danger')
                    return redirect(url_for('move'))

            try:
                mov = Movement(
                    ts=timestamp,
                    frm=frm,
                    to=to,
                    pname=product_name,
                    pqty=qty
                )
                db.session.add(mov)

                # Reduce product quantity in the product table
                product = Product.query.filter_by(prod_name=product_name).first()
                if product and product.prod_qty >= qty:
                    product.prod_qty -= qty
                else:
                    flash('Insufficient quantity for transfer', 'danger')
                    db.session.rollback()
                    return redirect(url_for('move'))

                db.session.commit()
                flash(f'{movement_type} recorded successfully', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error: {str(e)}', 'danger')

            return redirect(url_for('move'))

    return render_template('move.html', 
                         title='Transfers', 
                         form=form, 
                         details=details,
                         movement_types=[('Buy', 'Buy'), ('Sale', 'Sale'), ('Transfer', 'Transfer')])

def check(frm, to, name, qty, operation):
    product = Product.query.filter_by(prod_name=name).first()
    if not product:
        return False

    if operation == 'buy':
        product.prod_qty += qty
        
        warehouse_bal = Balance.query.filter_by(
            location='Warehouse',
            product=name
        ).first()
        
        if not warehouse_bal:
            warehouse_bal = Balance(
                location='Warehouse',
                product=name,
                quantity=qty
            )
            db.session.add(warehouse_bal)
        else:
            warehouse_bal.quantity += qty
        
        db.session.commit()
        return True

    elif operation == 'sale':
        warehouse_bal = Balance.query.filter_by(
            location='Warehouse',
            product=name
        ).first()
        
        if not warehouse_bal or warehouse_bal.quantity < qty:
            return False
        
        # Update stock
        product.prod_qty -= qty
        warehouse_bal.quantity -= qty
        db.session.commit()
        return True

    elif operation == 'transfer':
        from_bal = Balance.query.filter_by(
            location=frm,
            product=name
        ).first()
        
        if not from_bal or from_bal.quantity < qty:
            return 'no prod'
        
        to_bal = Balance.query.filter_by(
            location=to,
            product=name
        ).first()
        
        if not to_bal:
            to_bal = Balance(
                location=to,
                product=name,
                quantity=qty
            )
            db.session.add(to_bal)
        else:
            to_bal.quantity += qty
        
        from_bal.quantity -= qty
        db.session.commit()
        return True

    return False

@app.route("/delete")
def delete():
    pass  


@app.route("/edit_product/<int:product_id>", methods=['POST'])
def edit_product(product_id):
    print(f"Edit product route called with product_id: {product_id}") 
    product = Product.query.get_or_404(product_id)
    form = addproduct()
    if form.validate_on_submit():
        product.prod_name = form.prodname.data
        product.prod_qty = form.prodqty.data
        try:
            db.session.commit()
            flash(f'Product {form.prodname.data} updated successfully!', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Error updating product. Please try again.', 'danger')
    return redirect(url_for('product'))

@app.route("/delete_product/<int:product_id>", methods=['POST'])
def delete_product(product_id):
    print(f"Delete product route called with product_id: {product_id}")  # Debug log
    product = Product.query.get_or_404(product_id)
    try:
        db.session.delete(product)
        db.session.commit()
        flash(f'Product {product.prod_name} deleted successfully!', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('Error deleting product. Please try again.', 'danger')
    return redirect(url_for('product'))


@app.route('/overview')
def overview():
    products = Product.query.all()
    locations = Location.query.all()
    stock_data = {}

    for location in locations:
        location_stock = {}
        for product in products:
            total_in = db.session.query(db.func.sum(Movement.pqty)).filter(
                Movement.to == location.loc_name,
                Movement.pname == product.prod_name
            ).scalar() or 0
            
            
            total_out = db.session.query(db.func.sum(Movement.pqty)).filter(
                Movement.frm == location.loc_name,
                Movement.pname == product.prod_name
            ).scalar() or 0
            
            net_quantity = max(0, total_in - total_out) 
            location_stock[product.prod_name] = net_quantity
        
        stock_data[location.loc_name] = location_stock
    
    return render_template('overview.html',
                         products=products,
                         locations=locations,
                         stock_data=stock_data)

@app.route("/clear_history", methods=['POST'])
def clear_history():
    try:
        # Delete all records from the Movement table
        Movement.query.delete()
        db.session.commit()
        flash('All transaction history cleared successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error clearing history: {str(e)}', 'danger')
    return redirect(url_for('move'))